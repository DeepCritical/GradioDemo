"""Validator for querying available HuggingFace models and providers using OAuth token.

This module provides functions to:
1. Query available models from HuggingFace Hub
2. Query available inference providers (with dynamic discovery)
3. Validate model/provider combinations
4. Return formatted lists for Gradio dropdowns

Uses Hugging Face Hub API to discover providers dynamically by querying model
information. Falls back to known providers list if discovery fails.
"""

import asyncio
from time import time
from typing import Any

import structlog
from huggingface_hub import HfApi

from src.utils.config import settings

logger = structlog.get_logger()


def extract_oauth_token(oauth_token: Any) -> str | None:
    """Extract OAuth token value from Gradio OAuthToken object.

    Handles both gr.OAuthToken objects (with .token attribute) and plain strings.
    This is a convenience function for Gradio apps that use OAuth authentication.

    Args:
        oauth_token: Gradio OAuthToken object or string token

    Returns:
        Token string if available, None otherwise
    """
    if oauth_token is None:
        return None

    if hasattr(oauth_token, "token"):
        return oauth_token.token  # type: ignore[no-any-return]
    elif isinstance(oauth_token, str):
        return oauth_token

    logger.warning(
        "Could not extract token from OAuthToken object",
        oauth_token_type=type(oauth_token).__name__,
    )
    return None


# Known providers as fallback (updated from Hugging Face documentation)
# These are used when dynamic discovery fails or times out
KNOWN_PROVIDERS = [
    "auto",  # Auto-select (always available)
    "hf-inference",  # HuggingFace's own Inference API
    "nebius",
    "together",
    "scaleway",
    "hyperbolic",
    "novita",
    "nscale",
    "sambanova",
    "ovh",
    "fireworks-ai",  # Note: API uses "fireworks-ai", not "fireworks"
    "cerebras",
    "fal-ai",
    "cohere",
]


def get_provider_discovery_models() -> list[str]:
    """Get list of models to use for provider discovery.

    Reads from HF_FALLBACK_MODELS environment variable via settings.
    The environment variable should be a comma-separated list of model IDs.

    Returns:
        List of model IDs to query for provider discovery
    """
    # Get models from HF_FALLBACK_MODELS environment variable
    # This is automatically read by Pydantic Settings from the env var
    fallback_models = settings.get_hf_fallback_models_list()

    logger.debug(
        "Using HF_FALLBACK_MODELS for provider discovery",
        count=len(fallback_models),
        models=fallback_models,
    )

    return fallback_models


# Simple in-memory cache for provider lists (TTL: 1 hour)
_provider_cache: dict[str, tuple[list[str], float]] = {}
PROVIDER_CACHE_TTL = 3600  # 1 hour in seconds


async def get_available_providers(token: str | None = None) -> list[str]:
    """Get list of available inference providers.

    Discovers providers dynamically by querying model information from HuggingFace Hub.
    Uses caching to avoid repeated API calls. Falls back to known providers if discovery fails.

    Strategy:
    1. Check cache (if valid, return cached list)
    2. Query popular models to extract unique providers from their inferenceProviderMapping
    3. Fall back to known providers list if discovery fails
    4. Cache results for future use

    Args:
        token: Optional HuggingFace API token for authenticated requests
               Can be extracted from gr.OAuthToken.token in Gradio apps

    Returns:
        List of provider names sorted alphabetically, with "auto" first
        (e.g., ["auto", "fireworks-ai", "hf-inference", "nebius", ...])
    """
    # Check cache first
    cache_key = "providers" + (f"_{token[:8]}" if token else "_no_token")
    if cache_key in _provider_cache:
        cached_providers, cache_time = _provider_cache[cache_key]
        if time() - cache_time < PROVIDER_CACHE_TTL:
            logger.debug("Returning cached providers", count=len(cached_providers))
            return cached_providers

    try:
        providers = set(["auto"])  # Always include "auto"

        # Try dynamic discovery by querying popular models
        loop = asyncio.get_running_loop()
        api = HfApi(token=token)

        # Get models to query from HF_FALLBACK_MODELS environment variable via settings
        discovery_models = get_provider_discovery_models()

        # Query a sample of popular models to discover providers
        # This is more efficient than querying all models
        discovery_count = 0
        for model_id in discovery_models:
            try:

                def _get_model_info(m: str) -> Any:
                    """Get model info synchronously."""
                    return api.model_info(m, expand=["inferenceProviderMapping"])  # type: ignore[arg-type]

                info = await loop.run_in_executor(None, _get_model_info, model_id)

                # Extract providers from inference_provider_mapping
                if hasattr(info, "inference_provider_mapping") and info.inference_provider_mapping:
                    mapping = info.inference_provider_mapping
                    # mapping is a dict like {'hf-inference': InferenceProviderMapping(...), ...}
                    providers.update(mapping.keys())
                    discovery_count += 1
                    logger.debug(
                        "Discovered providers from model",
                        model=model_id,
                        providers=list(mapping.keys()),
                    )
            except Exception as e:
                logger.debug(
                    "Could not get provider info for model",
                    model=model_id,
                    error=str(e),
                )
                continue

        # If we discovered providers, use them; otherwise fall back to known providers
        if len(providers) > 1:  # More than just "auto"
            provider_list = sorted(list(providers))
            logger.info(
                "Discovered providers dynamically",
                count=len(provider_list),
                models_queried=discovery_count,
                has_token=bool(token),
            )
        else:
            # Fallback to known providers
            provider_list = KNOWN_PROVIDERS.copy()
            logger.info(
                "Using known providers list (discovery failed or incomplete)",
                count=len(provider_list),
                models_queried=discovery_count,
            )

        # Cache the results
        _provider_cache[cache_key] = (provider_list, time())

        return provider_list

    except Exception as e:
        logger.warning("Failed to get providers", error=str(e))
        # Return known providers as fallback
        return KNOWN_PROVIDERS.copy()


async def get_available_models(
    token: str | None = None,
    task: str = "text-generation",
    limit: int = 100,
    inference_provider: str | None = None,
) -> list[str]:
    """Get list of available models for text generation.

    Queries HuggingFace Hub API to get models that support text generation.
    Optionally filters by inference provider to show only models available via that provider.

    Args:
        token: Optional HuggingFace API token for authenticated requests
               Can be extracted from gr.OAuthToken.token in Gradio apps
        task: Task type to filter models (default: "text-generation")
        limit: Maximum number of models to return
        inference_provider: Optional provider name to filter models (e.g., "fireworks-ai", "nebius")
                           If None, returns all models for the task

    Returns:
        List of model IDs (e.g., ["meta-llama/Llama-3.1-8B-Instruct", ...])
    """
    try:
        loop = asyncio.get_running_loop()

        def _fetch_models() -> list[str]:
            """Fetch models synchronously in executor."""
            api = HfApi(token=token)

            # Build query parameters
            query_params: dict[str, Any] = {
                "task": task,
                "sort": "downloads",
                "direction": -1,
                "limit": limit,
            }

            # Filter by inference provider if specified
            if inference_provider and inference_provider != "auto":
                query_params["inference_provider"] = inference_provider

            # Search for models
            models = api.list_models(**query_params)

            # Extract model IDs
            model_ids = [model.id for model in models]
            return model_ids

        model_ids = await loop.run_in_executor(None, _fetch_models)

        logger.info(
            "Fetched available models",
            count=len(model_ids),
            task=task,
            provider=inference_provider or "all",
            has_token=bool(token),
        )

        return model_ids

    except Exception as e:
        logger.warning("Failed to get models from Hub API", error=str(e))
        # Return popular fallback models
        return [
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "HuggingFaceH4/zephyr-7b-beta",
            "google/gemma-2-9b-it",
        ]


async def validate_model_provider_combination(
    model_id: str,
    provider: str | None,
    token: str | None = None,
) -> tuple[bool, str | None]:
    """Validate that a model is available with a specific provider.

    Uses HuggingFace Hub API to check if the provider is listed in the model's
    inferenceProviderMapping. This is faster and more reliable than making test API calls.

    Args:
        model_id: HuggingFace model ID
        provider: Provider name (or None/empty for auto)
        token: Optional HuggingFace API token (from gr.OAuthToken.token)

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if combination is valid or provider is "auto"
        - error_message: Error message if invalid, None if valid
    """
    # "auto" is always valid - let HuggingFace select the provider
    if not provider or provider == "auto":
        return True, None

    try:
        loop = asyncio.get_running_loop()
        api = HfApi(token=token)

        def _get_model_info() -> Any:
            """Get model info with provider mapping synchronously."""
            return api.model_info(model_id, expand=["inferenceProviderMapping"])  # type: ignore[arg-type]

        info = await loop.run_in_executor(None, _get_model_info)

        # Check if provider is in the model's inference provider mapping
        if hasattr(info, "inference_provider_mapping") and info.inference_provider_mapping:
            mapping = info.inference_provider_mapping
            available_providers = set(mapping.keys())

            # Normalize provider name (some APIs use "fireworks-ai", others use "fireworks")
            normalized_provider = provider.lower()
            provider_variants = {normalized_provider}

            # Handle common provider name variations
            if normalized_provider == "fireworks":
                provider_variants.add("fireworks-ai")
            elif normalized_provider == "fireworks-ai":
                provider_variants.add("fireworks")

            # Check if any variant matches
            if any(p in available_providers for p in provider_variants):
                logger.debug(
                    "Model/provider combination validated via API",
                    model=model_id,
                    provider=provider,
                    available_providers=list(available_providers),
                )
                return True, None
            else:
                error_msg = (
                    f"Model {model_id} is not available with provider '{provider}'. "
                    f"Available providers: {', '.join(sorted(available_providers))}"
                )
                logger.debug(
                    "Model/provider combination invalid",
                    model=model_id,
                    provider=provider,
                    available_providers=list(available_providers),
                )
                return False, error_msg
        else:
            # Model doesn't have provider mapping - assume valid and let actual usage determine
            logger.debug(
                "Model has no provider mapping, assuming valid",
                model=model_id,
                provider=provider,
            )
            return True, None

    except Exception as e:
        logger.warning(
            "Model/provider validation failed",
            model=model_id,
            provider=provider,
            error=str(e),
        )
        # Don't fail validation on error - let the actual request fail
        # This is more user-friendly than blocking on validation errors
        return True, None


async def get_models_for_provider(
    provider: str,
    token: str | None = None,
    limit: int = 50,
) -> list[str]:
    """Get models available for a specific provider.

    This is a convenience wrapper around get_available_models() with provider filtering.

    Args:
        provider: Provider name (e.g., "nebius", "together", "fireworks-ai")
                  Note: Use "fireworks-ai" not "fireworks" for the API
        token: Optional HuggingFace API token (from gr.OAuthToken.token)
        limit: Maximum number of models to return

    Returns:
        List of model IDs available for the provider
    """
    # Normalize provider name for API
    normalized_provider = provider
    if provider.lower() == "fireworks":
        normalized_provider = "fireworks-ai"
        logger.debug("Normalized provider name", original=provider, normalized=normalized_provider)

    return await get_available_models(
        token=token,
        task="text-generation",
        limit=limit,
        inference_provider=normalized_provider,
    )


async def validate_oauth_token(token: str | None) -> dict[str, Any]:
    """Validate OAuth token and return available resources.

    Args:
        token: OAuth token to validate

    Returns:
        Dictionary with:
        - is_valid: Whether token is valid
        - has_inference_api_scope: Whether token has inference-api scope
        - available_models: List of available model IDs
        - available_providers: List of available provider names
        - username: HuggingFace username (if available)
        - error: Error message if validation failed
    """
    result: dict[str, Any] = {
        "is_valid": False,
        "has_inference_api_scope": False,
        "available_models": [],
        "available_providers": [],
        "username": None,
        "error": None,
    }

    if not token:
        result["error"] = "No token provided"
        return result

    try:
        # Validate token format
        from src.utils.hf_error_handler import validate_hf_token

        is_valid_format, format_error = validate_hf_token(token)
        if not is_valid_format:
            result["error"] = f"Invalid token format: {format_error}"
            return result

        # Try to get user info to validate token
        loop = asyncio.get_running_loop()

        def _get_user_info() -> dict[str, Any] | None:
            """Get user info from HuggingFace API."""
            try:
                api = HfApi(token=token)
                user_info = api.whoami()
                return user_info
            except Exception:
                return None

        user_info = await loop.run_in_executor(None, _get_user_info)

        if user_info:
            result["is_valid"] = True
            result["username"] = user_info.get("name") or user_info.get("fullname")
            logger.info("Token validated", username=result["username"])
        else:
            result["error"] = "Token validation failed - could not authenticate"
            return result

        # Try to query models to check inference-api scope
        try:
            models = await get_available_models(token=token, limit=10)
            if models:
                result["has_inference_api_scope"] = True
                result["available_models"] = models
                logger.info("Inference API scope confirmed", model_count=len(models))
        except Exception as e:
            logger.warning("Could not verify inference-api scope", error=str(e))
            # Token might be valid but without inference-api scope
            result["has_inference_api_scope"] = False
            result["error"] = f"Token may not have inference-api scope: {e}"

        # Get available providers
        try:
            providers = await get_available_providers(token=token)
            result["available_providers"] = providers
        except Exception as e:
            logger.warning("Could not get providers", error=str(e))
            # Use fallback providers
            result["available_providers"] = ["auto"]

        return result

    except Exception as e:
        logger.error("Token validation failed", error=str(e))
        result["error"] = str(e)
        return result
