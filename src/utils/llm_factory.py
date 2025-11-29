"""Centralized LLM client factory.

This module provides factory functions for creating LLM clients,
ensuring consistent configuration and clear error messages.

Agent-Framework Chat Clients:
- HuggingFace InferenceClient: Native function calling support via 'tools' parameter
- OpenAI ChatClient: Native function calling support (original implementation)
- Both can be used with agent-framework's ChatAgent

Pydantic AI Models:
- Default provider is HuggingFace (free tier, no API key required for public models)
- OpenAI and Anthropic are available as fallback options
- All providers use Pydantic AI's unified interface
"""

from typing import TYPE_CHECKING, Any

from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

if TYPE_CHECKING:
    from agent_framework.openai import OpenAIChatClient

    from src.utils.huggingface_chat_client import HuggingFaceChatClient


def get_magentic_client() -> "OpenAIChatClient":
    """
    Get the OpenAI client for Magentic agents (legacy function).

    Note: This function is kept for backward compatibility.
    For new code, use get_chat_client_for_agent() which supports
    both OpenAI and HuggingFace.

    Raises:
        ConfigurationError: If OPENAI_API_KEY is not set

    Returns:
        Configured OpenAIChatClient for Magentic agents
    """
    # Import here to avoid requiring agent-framework for simple mode
    from agent_framework.openai import OpenAIChatClient

    api_key = settings.get_openai_api_key()

    return OpenAIChatClient(
        model_id=settings.openai_model,
        api_key=api_key,
    )


def get_huggingface_chat_client() -> "HuggingFaceChatClient":
    """
    Get HuggingFace chat client for agent-framework.

    HuggingFace InferenceClient natively supports function calling,
    making it compatible with agent-framework's ChatAgent.

    Returns:
        Configured HuggingFaceChatClient

    Raises:
        ConfigurationError: If initialization fails
    """
    from src.utils.huggingface_chat_client import HuggingFaceChatClient

    model_name = settings.huggingface_model or "Qwen/Qwen3-Next-80B-A3B-Thinking"
    api_key = settings.hf_token or settings.huggingface_api_key

    return HuggingFaceChatClient(
        model_name=model_name,
        api_key=api_key,
        provider="auto",  # Auto-select best provider
    )


def get_chat_client_for_agent() -> Any:
    """
    Get appropriate chat client for agent-framework based on configuration.

    Supports:
    - HuggingFace InferenceClient (if HF_TOKEN available, preferred for free tier)
    - OpenAI ChatClient (if OPENAI_API_KEY available, fallback)

    Returns:
        ChatClient compatible with agent-framework (HuggingFaceChatClient or OpenAIChatClient)

    Raises:
        ConfigurationError: If no suitable client can be created
    """
    # Prefer HuggingFace if available (free tier)
    if settings.has_huggingface_key:
        return get_huggingface_chat_client()

    # Fallback to OpenAI if available
    if settings.has_openai_key:
        return get_magentic_client()

    # If neither available, try HuggingFace without key (public models)
    try:
        return get_huggingface_chat_client()
    except Exception:
        pass

    raise ConfigurationError(
        "No chat client available. Set HF_TOKEN or OPENAI_API_KEY for agent-framework mode."
    )


def get_pydantic_ai_model() -> Any:
    """
    Get the appropriate model for pydantic-ai based on configuration.

    Uses the configured LLM_PROVIDER to select between HuggingFace, OpenAI, and Anthropic.
    Defaults to HuggingFace if provider is not specified or unknown.
    This is used by simple mode components (JudgeHandler, etc.)

    Returns:
        Configured pydantic-ai model
    """
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.models.openai import OpenAIModel  # type: ignore[attr-defined]

    # Try to import HuggingFace support (may not be available in all pydantic-ai versions)
    # According to https://ai.pydantic.dev/models/huggingface/, HuggingFace support requires
    # pydantic-ai with huggingface extra or pydantic-ai-slim[huggingface]
    # There are two ways to use HuggingFace:
    # 1. Inference API: HuggingFaceModel with HuggingFaceProvider (uses AsyncInferenceClient internally)
    # 2. Local models: Would use transformers directly (not via pydantic-ai)
    try:
        from huggingface_hub import AsyncInferenceClient
        from pydantic_ai.models.huggingface import HuggingFaceModel
        from pydantic_ai.providers.huggingface import HuggingFaceProvider

        _HUGGINGFACE_AVAILABLE = True  # noqa: N806
    except ImportError:
        HuggingFaceModel = None  # type: ignore[assignment, misc]  # noqa: N806
        HuggingFaceProvider = None  # type: ignore[assignment, misc]  # noqa: N806
        AsyncInferenceClient = None  # type: ignore[assignment, misc]  # noqa: N806
        _HUGGINGFACE_AVAILABLE = False  # noqa: N806

    if settings.llm_provider == "huggingface":
        if not _HUGGINGFACE_AVAILABLE:
            raise ConfigurationError(
                "HuggingFace models are not available in this version of pydantic-ai. "
                "Please install with: uv add 'pydantic-ai[huggingface]' or set LLM_PROVIDER to 'openai'/'anthropic'."
            )
        # Inference API - uses HuggingFace Inference API via AsyncInferenceClient
        # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
        model_name = settings.huggingface_model or "Qwen/Qwen3-Next-80B-A3B-Thinking"
        # Create AsyncInferenceClient for inference API
        hf_client = AsyncInferenceClient(api_key=settings.hf_token)  # type: ignore[misc]
        # Pass client to HuggingFaceProvider for inference API usage
        provider = HuggingFaceProvider(hf_client=hf_client)  # type: ignore[misc]
        return HuggingFaceModel(model_name, provider=provider)  # type: ignore[misc]

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY not set for pydantic-ai")
        return OpenAIModel(settings.openai_model, api_key=settings.openai_api_key)  # type: ignore[call-overload]

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ConfigurationError("ANTHROPIC_API_KEY not set for pydantic-ai")
        return AnthropicModel(settings.anthropic_model, api_key=settings.anthropic_api_key)  # type: ignore[call-arg]

    # Default to HuggingFace if provider is unknown or not specified
    if not _HUGGINGFACE_AVAILABLE:
        raise ConfigurationError(
            "HuggingFace models are not available in this version of pydantic-ai. "
            "Please install with: uv add 'pydantic-ai[huggingface]' or set LLM_PROVIDER to 'openai'/'anthropic'."
        )
    # Inference API - uses HuggingFace Inference API via AsyncInferenceClient
    # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
    model_name = settings.huggingface_model or "Qwen/Qwen3-Next-80B-A3B-Thinking"
    # Create AsyncInferenceClient for inference API
    hf_client = AsyncInferenceClient(api_key=settings.hf_token)  # type: ignore[misc]
    # Pass client to HuggingFaceProvider for inference API usage
    provider = HuggingFaceProvider(hf_client=hf_client)  # type: ignore[misc]
    return HuggingFaceModel(model_name, provider=provider)  # type: ignore[misc]


def check_magentic_requirements() -> None:
    """
    Check if Magentic/agent-framework mode requirements are met.

    Note: HuggingFace InferenceClient now supports function calling natively,
    so this check is relaxed. We prefer HuggingFace if available, fallback to OpenAI.

    Raises:
        ConfigurationError: If no suitable client can be created
    """
    # Try to get a chat client - will raise if none available
    try:
        get_chat_client_for_agent()
    except ConfigurationError as e:
        raise ConfigurationError(
            "Agent-framework mode requires HF_TOKEN or OPENAI_API_KEY. "
            "HuggingFace is preferred (free tier with function calling support). "
            "Use mode='simple' for other LLM providers."
        ) from e


def check_simple_mode_requirements() -> None:
    """
    Check if simple mode requirements are met.

    Simple mode supports HuggingFace (default), OpenAI, and Anthropic.
    HuggingFace can work without an API key for public models.

    Raises:
        ConfigurationError: If no LLM is available (only if explicitly required)
    """
    # HuggingFace can work without API key for public models, so we don't require it
    # This allows simple mode to work out of the box
    pass
