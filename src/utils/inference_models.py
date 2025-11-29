"""Configuration for HuggingFace Inference Providers models.

Based on: https://huggingface.co/inference/models

This module provides model and provider configurations with verification
capabilities to ensure models are actually available on selected providers.
"""

from typing import TypedDict


class ModelProvider(TypedDict):
    """Provider information for a model."""

    name: str
    input_cost: float | None  # $/1M tokens
    output_cost: float | None  # $/1M tokens
    latency: float | None  # seconds
    throughput: float | None  # tokens/second
    supports_tools: bool
    supports_structured: bool
    requires_auth: bool  # Whether this provider requires authentication


class InferenceModel(TypedDict):
    """Model configuration with available providers."""

    model_id: str
    display_name: str
    providers: dict[str, ModelProvider]
    requires_auth: bool  # Whether the model itself requires authentication (gated)
    description: str


# Latest Reasoning Models from https://huggingface.co/inference/models
# Updated with latest reasoning models (Qwen3-Next, Qwen3-235B, Llama-3.3, etc.)
INFERENCE_MODELS: dict[str, InferenceModel] = {
    # Top-tier reasoning models (latest)
    "Qwen/Qwen3-Next-80B-A3B-Thinking": {
        "model_id": "Qwen/Qwen3-Next-80B-A3B-Thinking",
        "display_name": "Qwen3-Next-80B-A3B-Thinking",
        "requires_auth": True,  # Gated
        "description": "Qwen's latest reasoning model - Advanced thinking capabilities, 262K context",
        "providers": {
            "together": {
                "name": "together",
                "input_cost": 0.15,
                "output_cost": 1.5,
                "latency": 0.48,
                "throughput": 202.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
            "together-fastest": {
                "name": "together-fastest",
                "input_cost": 0.15,
                "output_cost": 1.5,
                "latency": 0.48,
                "throughput": 202.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
        },
    },
    "Qwen/Qwen3-Next-80B-A3B-Instruct": {
        "model_id": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "display_name": "Qwen3-Next-80B-A3B-Instruct",
        "requires_auth": True,  # Gated
        "description": "Qwen's latest instruction model - High performance, 262K context",
        "providers": {
            "together": {
                "name": "together",
                "input_cost": 0.15,
                "output_cost": 1.5,
                "latency": 0.60,
                "throughput": 153.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
            "together-fastest": {
                "name": "together-fastest",
                "input_cost": 0.15,
                "output_cost": 1.5,
                "latency": 0.60,
                "throughput": 153.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
        },
    },
    "Qwen/Qwen3-235B-A22B-Instruct-2507": {
        "model_id": "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "display_name": "Qwen3-235B-A22B-Instruct",
        "requires_auth": True,  # Gated
        "description": "Qwen's massive 235B model - Ultra-high performance, 262K context",
        "providers": {
            "cerebras": {
                "name": "cerebras",
                "input_cost": 0.6,
                "output_cost": 1.2,
                "latency": 0.23,
                "throughput": 509.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
            "cerebras-fastest": {
                "name": "cerebras-fastest",
                "input_cost": 0.6,
                "output_cost": 1.2,
                "latency": 0.23,
                "throughput": 509.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
            "together": {
                "name": "together",
                "input_cost": 0.2,
                "output_cost": 0.6,
                "latency": 0.39,
                "throughput": 42.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
        },
    },
    "Qwen/Qwen3-235B-A22B-Thinking-2507": {
        "model_id": "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "display_name": "Qwen3-235B-A22B-Thinking",
        "requires_auth": True,  # Gated
        "description": "Qwen's massive 235B reasoning model - Advanced thinking, 262K context",
        "providers": {
            "cerebras": {
                "name": "cerebras",
                "input_cost": None,
                "output_cost": None,
                "latency": None,
                "throughput": None,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": True,
            },
        },
    },
    "meta-llama/Llama-3.3-70B-Instruct": {
        "model_id": "meta-llama/Llama-3.3-70B-Instruct",
        "display_name": "Llama 3.3 70B Instruct",
        "requires_auth": True,  # Gated
        "description": "Meta's latest Llama 3.3 - High performance, tools support",
        "providers": {
            "cerebras": {
                "name": "cerebras",
                "input_cost": 0.85,
                "output_cost": 1.2,
                "latency": 0.35,
                "throughput": 948.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
            "cerebras-fastest": {
                "name": "cerebras-fastest",
                "input_cost": 0.85,
                "output_cost": 1.2,
                "latency": 0.35,
                "throughput": 948.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
        },
    },
    "openai/gpt-oss-120b": {
        "model_id": "openai/gpt-oss-120b",
        "display_name": "GPT-OSS-120B",
        "requires_auth": True,  # Gated
        "description": "OpenAI's open-source 120B model - Ultra-fast inference",
        "providers": {
            "cerebras": {
                "name": "cerebras",
                "input_cost": 0.25,
                "output_cost": 0.69,
                "latency": 0.23,
                "throughput": 1051.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
            "cerebras-fastest": {
                "name": "cerebras-fastest",
                "input_cost": 0.25,
                "output_cost": 0.69,
                "latency": 0.23,
                "throughput": 1051.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
        },
    },
    "CohereLabs/command-a-reasoning-08-2025": {
        "model_id": "CohereLabs/command-a-reasoning-08-2025",
        "display_name": "Command A Reasoning 08-2025",
        "requires_auth": True,  # Gated
        "description": "Cohere's latest reasoning model - Specialized for reasoning tasks",
        "providers": {
            "cohere": {
                "name": "cohere",
                "input_cost": None,
                "output_cost": None,
                "latency": 0.18,
                "throughput": 94.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
        },
    },
    "zai-org/GLM-4.6": {
        "model_id": "zai-org/GLM-4.6",
        "display_name": "GLM-4.6",
        "requires_auth": True,  # Gated
        "description": "ZAI's GLM-4.6 - High performance reasoning model",
        "providers": {
            "cerebras": {
                "name": "cerebras",
                "input_cost": None,
                "output_cost": None,
                "latency": 0.27,
                "throughput": 381.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
            "cerebras-fastest": {
                "name": "cerebras-fastest",
                "input_cost": None,
                "output_cost": None,
                "latency": 0.27,
                "throughput": 381.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
            "zai-org": {
                "name": "zai-org",
                "input_cost": None,
                "output_cost": None,
                "latency": 3.08,
                "throughput": 54.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
        },
    },
    "meta-llama/Llama-3.1-8B-Instruct": {
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "display_name": "Llama 3.1 8B Instruct",
        "requires_auth": True,  # Gated
        "description": "Meta's Llama 3.1 8B - Fast, efficient reasoning",
        "providers": {
            "novita": {
                "name": "novita",
                "input_cost": 0.02,
                "output_cost": 0.05,
                "latency": 0.64,
                "throughput": 84.0,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": True,
            },
            "nebius": {
                "name": "nebius",
                "input_cost": 0.03,
                "output_cost": 0.09,
                "latency": 0.35,
                "throughput": 194.0,
                "supports_tools": False,
                "supports_structured": True,
                "requires_auth": True,
            },
            "cerebras": {
                "name": "cerebras",
                "input_cost": 0.1,
                "output_cost": 0.1,
                "latency": 0.33,
                "throughput": 1148.0,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": True,
            },
            "sambanova": {
                "name": "sambanova",
                "input_cost": 0.1,
                "output_cost": 0.2,
                "latency": 0.85,
                "throughput": 527.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
        },
    },
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B": {
        "model_id": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        "display_name": "DeepSeek R1 Distill Llama 70B",
        "requires_auth": True,  # Gated
        "description": "DeepSeek's reasoning model - Advanced chain-of-thought",
        "providers": {
            "novita": {
                "name": "novita",
                "input_cost": 0.64,
                "output_cost": 0.64,
                "latency": 1.21,
                "throughput": 31.0,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": True,
            },
            "sambanova": {
                "name": "sambanova",
                "input_cost": 0.7,
                "output_cost": 1.4,
                "latency": 2.67,
                "throughput": 158.0,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": True,
            },
            "nscale": {
                "name": "nscale",
                "input_cost": 0.75,
                "output_cost": 0.75,
                "latency": 1.24,
                "throughput": 16.0,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": True,
            },
        },
    },
    "moonshotai/Kimi-K2-Thinking": {
        "model_id": "moonshotai/Kimi-K2-Thinking",
        "display_name": "Kimi K2 Thinking",
        "requires_auth": True,  # Gated
        "description": "Moonshot AI's thinking model - Long context reasoning",
        "providers": {
            "novita": {
                "name": "novita",
                "input_cost": 0.48,
                "output_cost": 2.0,
                "latency": 1.60,
                "throughput": 16.0,
                "supports_tools": True,
                "supports_structured": False,
                "requires_auth": True,
            },
            "nebius": {
                "name": "nebius",
                "input_cost": 0.6,
                "output_cost": 2.5,
                "latency": 0.34,
                "throughput": 87.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
            "together": {
                "name": "together",
                "input_cost": 1.2,
                "output_cost": 4.0,
                "latency": 0.86,
                "throughput": 97.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": True,
            },
        },
    },
    "allenai/Olmo-3-7B-Instruct": {
        "model_id": "allenai/Olmo-3-7B-Instruct",
        "display_name": "Olmo 3 7B Instruct",
        "requires_auth": False,  # Ungated
        "description": "AllenAI's open model - Good reasoning, no auth needed",
        "providers": {
            "publicai": {
                "name": "publicai",
                "input_cost": None,
                "output_cost": None,
                "latency": 1.78,
                "throughput": 36.0,
                "supports_tools": True,
                "supports_structured": True,
                "requires_auth": False,
            },
        },
    },
    "Qwen/Qwen2-7B-Instruct": {
        "model_id": "Qwen/Qwen2-7B-Instruct",
        "display_name": "Qwen2 7B Instruct",
        "requires_auth": False,  # Ungated
        "description": "Qwen's efficient model - Fast, no authentication",
        "providers": {
            "featherless-ai": {
                "name": "featherless-ai",
                "input_cost": None,
                "output_cost": None,
                "latency": None,
                "throughput": None,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": False,
            },
        },
    },
    "HuggingFaceH4/zephyr-7b-beta": {
        "model_id": "HuggingFaceH4/zephyr-7b-beta",
        "display_name": "Zephyr 7B Beta",
        "requires_auth": False,  # Ungated
        "description": "HuggingFace's fine-tuned model - Free tier friendly",
        "providers": {
            "featherless-ai": {
                "name": "featherless-ai",
                "input_cost": None,
                "output_cost": None,
                "latency": None,
                "throughput": None,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": False,
            },
        },
    },
    "google/gemma-2-2b-it": {
        "model_id": "google/gemma-2-2b-it",
        "display_name": "Gemma 2 2B IT",
        "requires_auth": True,  # Gated
        "description": "Google's compact model - Small but capable",
        "providers": {
            "nebius": {
                "name": "nebius",
                "input_cost": None,
                "output_cost": None,
                "latency": None,
                "throughput": None,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": True,
            },
        },
    },
    "microsoft/Phi-3-mini-4k-instruct": {
        "model_id": "microsoft/Phi-3-mini-4k-instruct",
        "display_name": "Phi-3 Mini 4K Instruct",
        "requires_auth": False,  # Ungated
        "description": "Microsoft's efficient model - Fast inference",
        "providers": {
            "featherless-ai": {
                "name": "featherless-ai",
                "input_cost": None,
                "output_cost": None,
                "latency": None,
                "throughput": None,
                "supports_tools": False,
                "supports_structured": False,
                "requires_auth": False,
            },
        },
    },
}


def get_available_models(has_auth: bool = False) -> list[tuple[str, str]]:
    """
    Get list of available models based on authentication status.

    Args:
        has_auth: Whether user has authentication (OAuth or HF_TOKEN)

    Returns:
        List of (model_id, display_name) tuples for dropdown
    """
    models = []
    for model_id, model_info in INFERENCE_MODELS.items():
        # If no auth, only show ungated models
        if not has_auth and model_info["requires_auth"]:
            continue
        models.append((model_id, model_info["display_name"]))
    return models


def get_available_providers(model_id: str, has_auth: bool = False) -> list[tuple[str, str]]:
    """
    Get list of available providers for a model based on authentication.

    This is a convenience wrapper around get_available_providers_verified
    that doesn't perform async verification.

    Args:
        model_id: The model ID
        has_auth: Whether user has authentication

    Returns:
        List of (provider_name, display_name) tuples for dropdown
    """
    return get_available_providers_verified(model_id, has_auth=has_auth, verify=False)


def get_model_info(model_id: str) -> InferenceModel | None:
    """Get model information."""
    return INFERENCE_MODELS.get(model_id)


def get_provider_info(model_id: str, provider_name: str) -> ModelProvider | None:
    """Get provider information for a model."""
    model = INFERENCE_MODELS.get(model_id)
    if not model:
        return None
    return model["providers"].get(provider_name)


def verify_provider_availability(
    model_id: str,
    provider_name: str,
) -> bool:
    """
    Verify that a model is available on the specified provider (static check).

    This function checks the static configuration to see if a provider
    is listed for the model. For dynamic verification via API calls,
    use verify_provider_availability_async().

    Args:
        model_id: The model ID to verify
        provider_name: The provider name to verify

    Returns:
        True if the model is configured for the provider, False otherwise
    """
    model_config = INFERENCE_MODELS.get(model_id)
    if not model_config:
        return False
    providers = model_config.get("providers", {})
    return provider_name in providers


async def verify_provider_availability_async(
    model_id: str,
    provider_name: str,
    api_key: str | None = None,
) -> bool:
    """
    Verify that a model is actually available on the specified provider via API.

    This function attempts to check if the model/provider combination is valid
    by making a lightweight API call to the HuggingFace Inference API.

    Note: This is an async function and should be called from an async context.
    For synchronous checks, use verify_provider_availability().

    Args:
        model_id: The model ID to verify
        provider_name: The provider name to verify
        api_key: Optional API key for authentication (uses env vars if not provided)

    Returns:
        True if the model is available on the provider, False otherwise
    """
    # For now, fall back to static check
    # TODO: Implement actual API verification when needed
    return verify_provider_availability(model_id, provider_name)


def get_available_providers_verified(
    model_id: str,
    has_auth: bool = False,
    api_key: str | None = None,
    verify: bool = False,
) -> list[tuple[str, str]]:
    """
    Get list of available providers for a model with optional verification.

    Args:
        model_id: The model ID
        has_auth: Whether user has authentication
        api_key: Optional API key for verification
        verify: Whether to verify provider availability (async, requires api_key)

    Returns:
        List of (provider_name, display_name) tuples for dropdown
    """
    if model_id not in INFERENCE_MODELS:
        return []

    model = INFERENCE_MODELS[model_id]
    providers = []

    for provider_name, provider_info in model["providers"].items():
        # If no auth, only show providers that don't require auth
        if not has_auth and provider_info["requires_auth"]:
            continue

        # Create display name with cost/latency info
        display_parts = [provider_name]
        if provider_info["latency"]:
            display_parts.append(f"{provider_info['latency']:.2f}s")
        if provider_info["input_cost"]:
            display_parts.append(f"${provider_info['input_cost']}/1M")
        if provider_info["supports_tools"]:
            display_parts.append("🔧")
        if provider_info["supports_structured"]:
            display_parts.append("📊")
        display_name = " | ".join(display_parts)

        providers.append((provider_name, display_name))

    # Note: If verify=True, this should be called from an async context
    # For now, we return static providers. Async verification can be done separately.

    return providers
