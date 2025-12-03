"""Main Gradio application for DeepCritical research agent.

This module provides the Gradio interface with:
- OAuth authentication via HuggingFace
- Multimodal input support (text, images, audio)
- Research agent orchestration
- Real-time event streaming
- MCP server integration
"""

import os
from collections.abc import AsyncGenerator
from typing import Any

import gradio as gr
import numpy as np
import structlog

from src.agent_factory.judges import HFInferenceJudgeHandler, JudgeHandler, MockJudgeHandler
from src.orchestrator_factory import create_orchestrator
from src.services.multimodal_processing import get_multimodal_service
from src.utils.config import settings
from src.utils.models import AgentEvent, OrchestratorConfig

# Import ModelMessage from pydantic_ai with fallback
try:
    from pydantic_ai import ModelMessage
except ImportError:
    from typing import Any

    ModelMessage = Any  # type: ignore[assignment, misc]

# Type alias for Gradio multimodal input
MultimodalPostprocess = dict[str, Any] | str

# Import HuggingFace components with graceful fallback
try:
    from pydantic_ai.models.huggingface import HuggingFaceModel
    from pydantic_ai.providers.huggingface import HuggingFaceProvider

    _HUGGINGFACE_AVAILABLE = True
except ImportError:
    _HUGGINGFACE_AVAILABLE = False
    HuggingFaceModel = None  # type: ignore[assignment, misc]
    HuggingFaceProvider = None  # type: ignore[assignment, misc]

try:
    from huggingface_hub import AsyncInferenceClient

    _ASYNC_INFERENCE_AVAILABLE = True
except ImportError:
    _ASYNC_INFERENCE_AVAILABLE = False
    AsyncInferenceClient = None  # type: ignore[assignment, misc]

logger = structlog.get_logger()


def configure_orchestrator(
    use_mock: bool = False,
    mode: str = "simple",
    oauth_token: str | None = None,
    hf_model: str | None = None,
    hf_provider: str | None = None,
    graph_mode: str | None = None,
    use_graph: bool = True,
    web_search_provider: str | None = None,
) -> tuple[Any, str]:
    """
    Configure and create the research orchestrator.

    Args:
        use_mock: Force mock judge handler (for testing)
        mode: Orchestrator mode ("simple", "iterative", "deep", "auto", "advanced")
        oauth_token: Optional OAuth token from HuggingFace login (takes priority over env vars)
        hf_model: Optional HuggingFace model ID (overrides settings)
        hf_provider: Optional inference provider (currently not used by HuggingFaceProvider)
        graph_mode: Optional graph execution mode
        use_graph: Whether to use graph execution
        web_search_provider: Optional web search provider ("auto", "serper", "duckduckgo")

    Returns:
        Tuple of (orchestrator, backend_info_string)
    """
    from src.tools.search_handler import SearchHandler
    from src.tools.web_search_factory import create_web_search_tool

    # Create search handler with tools
    tools = []

    # Add web search tool
    web_search_tool = create_web_search_tool(provider=web_search_provider or "auto")
    if web_search_tool:
        tools.append(web_search_tool)
        logger.info("Web search tool added to search handler", provider=web_search_tool.name)

    # Create config if not provided
    config = OrchestratorConfig()

    search_handler = SearchHandler(
        tools=tools,
        timeout=config.search_timeout,
        include_rag=True,
        auto_ingest_to_rag=True,
        oauth_token=oauth_token,
    )

    # Create judge (mock, real, or free tier)
    judge_handler: JudgeHandler | MockJudgeHandler | HFInferenceJudgeHandler
    backend_info = "Unknown"

    # 1. Forced Mock (Unit Testing)
    if use_mock:
        judge_handler = MockJudgeHandler()
        backend_info = "Mock (Testing)"

    # 2. API Key (OAuth or Env) - HuggingFace only (OAuth provides HF token)
    # Priority: oauth_token > env vars
    # On HuggingFace Spaces, OAuth token is available via request.oauth_token
    #
    # OAuth Scope Requirements:
    # - 'inference-api': Required for HuggingFace Inference API access
    #   This scope grants access to:
    #   * HuggingFace's own Inference API
    #   * All third-party inference providers (nebius, together, scaleway, hyperbolic, novita, nscale, sambanova, ovh, fireworks, etc.)
    #   * All models available through the Inference Providers API
    #   See: https://huggingface.co/docs/hub/oauth#currently-supported-scopes
    #
    # Note: The hf_provider parameter is accepted but not used here because HuggingFaceProvider
    # from pydantic-ai doesn't support provider selection. Provider selection happens at the
    # InferenceClient level (used in HuggingFaceChatClient for advanced mode).
    effective_api_key = oauth_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")

    # Log which authentication source is being used
    if effective_api_key:
        auth_source = (
            "OAuth token"
            if oauth_token
            else ("HF_TOKEN env var" if os.getenv("HF_TOKEN") else "HUGGINGFACE_API_KEY env var")
        )
        logger.info(
            "Using HuggingFace authentication",
            source=auth_source,
            has_token=bool(effective_api_key),
        )

    if effective_api_key:
        # We have an API key (OAuth or env) - use pydantic-ai with JudgeHandler
        # This uses HuggingFace Inference API, which includes access to all third-party providers
        # via the Inference Providers API (router.huggingface.co)
        model: Any | None = None
        # Use selected model or fall back to env var/settings
        model_name = (
            hf_model
            or os.getenv("HF_MODEL")
            or settings.huggingface_model
            or "Qwen/Qwen3-Next-80B-A3B-Thinking"
        )
        if not _HUGGINGFACE_AVAILABLE:
            raise ImportError(
                "HuggingFace models are not available in this version of pydantic-ai. "
                "Please install with: uv add 'pydantic-ai[huggingface]' to use HuggingFace inference providers."
            )
        # Inference API - uses HuggingFace Inference API
        # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
        # HuggingFaceProvider accepts api_key parameter directly
        # This is consistent with usage in src/utils/llm_factory.py and src/agent_factory/judges.py
        # The OAuth token with 'inference-api' scope provides access to all inference providers
        provider = HuggingFaceProvider(api_key=effective_api_key)  # type: ignore[misc]
        model = HuggingFaceModel(model_name, provider=provider)  # type: ignore[misc]
        backend_info = "API (HuggingFace OAuth)" if oauth_token else "API (Env Config)"

        judge_handler = JudgeHandler(model=model)

    # 3. Free Tier (HuggingFace Inference) - NO API KEY AVAILABLE
    else:
        # No API key available - use HFInferenceJudgeHandler with public models
        # HFInferenceJudgeHandler will use HF_TOKEN from env if available, otherwise public models
        # Note: OAuth token should have been caught in effective_api_key check above
        # If we reach here, we truly have no API key, so use public models
        judge_handler = HFInferenceJudgeHandler(
            model_id=hf_model if hf_model else None,
            api_key=None,  # Will use HF_TOKEN from env if available, otherwise public models
        )
        model_display = hf_model.split("/")[-1] if hf_model else "Default (Public Models)"
        backend_info = f"Free Tier ({model_display} - Public Models Only)"

    # Determine effective mode
    # If mode is already iterative/deep/auto, use it directly
    # If mode is "graph" or "simple", use graph_mode if provided
    effective_mode = mode
    if mode in ("graph", "simple") and graph_mode:
        effective_mode = graph_mode
    elif mode == "graph" and not graph_mode:
        effective_mode = "auto"  # Default to auto if graph mode but no graph_mode specified

    orchestrator = create_orchestrator(
        search_handler=search_handler,
        judge_handler=judge_handler,
        config=config,
        mode=effective_mode,  # type: ignore
        oauth_token=oauth_token,
    )

    return orchestrator, backend_info


def _is_file_path(text: str) -> bool:
    """Check if text appears to be a file path.

    Args:
        text: Text to check

    Returns:
        True if text looks like a file path
    """
    return ("/" in text or "\\" in text) and (
        "." in text.split("/")[-1] or "." in text.split("\\")[-1]
    )


def event_to_chat_message(event: AgentEvent) -> dict[str, Any]:
    """Convert AgentEvent to Gradio chat message format.

    Args:
        event: AgentEvent to convert

    Returns:
        Dictionary with 'role' and 'content' keys for Gradio Chatbot
    """
    result: dict[str, Any] = {
        "role": "assistant",
        "content": event.to_markdown(),
    }

    # Add metadata if available
    if event.data:
        metadata: dict[str, Any] = {}

        # Extract file path if present
        if isinstance(event.data, dict):
            file_path = event.data.get("file_path")
            if file_path:
                metadata["file_path"] = file_path

        if metadata:
            result["metadata"] = metadata
    return result


def extract_oauth_info(request: gr.Request | None) -> tuple[str | None, str | None]:
    """
    Extract OAuth token and username from Gradio request.

    Args:
        request: Gradio request object containing OAuth information

    Returns:
        Tuple of (oauth_token, oauth_username)
    """
    oauth_token: str | None = None
    oauth_username: str | None = None

    if request is None:
        return oauth_token, oauth_username

    # Try multiple ways to access OAuth token (Gradio API may vary)
    # Pattern 1: request.oauth_token.token
    if hasattr(request, "oauth_token") and request.oauth_token is not None:
        if hasattr(request.oauth_token, "token"):
            oauth_token = request.oauth_token.token
        elif isinstance(request.oauth_token, str):
            oauth_token = request.oauth_token
    # Pattern 2: request.headers (fallback)
    elif hasattr(request, "headers"):
        # OAuth token might be in headers
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            oauth_token = auth_header.replace("Bearer ", "")

    # Access username from request
    if hasattr(request, "username") and request.username:
        oauth_username = request.username
    # Also try accessing via oauth_profile if available
    elif hasattr(request, "oauth_profile") and request.oauth_profile is not None:
        if hasattr(request.oauth_profile, "username") and request.oauth_profile.username:
            oauth_username = request.oauth_profile.username
        elif hasattr(request.oauth_profile, "name") and request.oauth_profile.name:
            oauth_username = request.oauth_profile.name

    return oauth_token, oauth_username


async def yield_auth_messages(
    oauth_username: str | None,
    oauth_token: str | None,
    has_huggingface: bool,
    mode: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Yield authentication status messages.

    Args:
        oauth_username: OAuth username if available
        oauth_token: OAuth token if available
        has_huggingface: Whether HuggingFace authentication is available
        mode: Research mode

    Yields:
        Chat message dictionaries
    """
    if oauth_username:
        yield {
            "role": "assistant",
            "content": f"👋 **Welcome, {oauth_username}!**\n\nAuthenticated via HuggingFace OAuth.",
        }

    if oauth_token:
        yield {
            "role": "assistant",
            "content": (
                "🔐 **Authentication Status**: ✅ Authenticated\n\n"
                "Your OAuth token has been validated. You can now use all AI models and research tools."
            ),
        }
    elif has_huggingface:
        yield {
            "role": "assistant",
            "content": (
                "🔐 **Authentication Status**: ✅ Using environment token\n\n"
                "Using HF_TOKEN from environment variables."
            ),
        }
    else:
        yield {
            "role": "assistant",
            "content": (
                "⚠️ **Authentication Status**: ❌ No authentication\n\n"
                "Please sign in with HuggingFace or set HF_TOKEN environment variable."
            ),
        }

    yield {
        "role": "assistant",
        "content": f"🚀 **Mode**: {mode.upper()}\n\nStarting research agent...",
    }


def _extract_oauth_token(oauth_token: gr.OAuthToken | None) -> str | None:
    """Extract token value from OAuth token object."""
    if oauth_token is None:
        return None

    if hasattr(oauth_token, "token"):
        token_value: str | None = getattr(oauth_token, "token", None)  # type: ignore[assignment]
        if token_value is None:
            return None
        logger.debug("OAuth token extracted from oauth_token.token attribute")

        # Validate token format
        from src.utils.hf_error_handler import log_token_info, validate_hf_token

        log_token_info(token_value, context="research_agent")
        is_valid, error_msg = validate_hf_token(token_value)
        if not is_valid:
            logger.warning(
                "OAuth token validation failed",
                error=error_msg,
                oauth_token_type=type(oauth_token).__name__,
            )
        return token_value

    if isinstance(oauth_token, str):
        logger.debug("OAuth token extracted as string")

        # Validate token format
        from src.utils.hf_error_handler import log_token_info, validate_hf_token

        log_token_info(oauth_token, context="research_agent")
        return oauth_token

    logger.warning(
        "OAuth token object present but token extraction failed",
        oauth_token_type=type(oauth_token).__name__,
    )
    return None


def _extract_username(oauth_profile: gr.OAuthProfile | None) -> str | None:
    """Extract username from OAuth profile."""
    if oauth_profile is None:
        return None

    username: str | None = None
    if hasattr(oauth_profile, "username") and oauth_profile.username:
        username = str(oauth_profile.username)
    elif hasattr(oauth_profile, "name") and oauth_profile.name:
        username = str(oauth_profile.name)

    if username:
        logger.info("OAuth user authenticated", username=username)
    return username


async def _process_multimodal_input(
    message: str | MultimodalPostprocess,
    enable_image_input: bool,
    enable_audio_input: bool,
    token_value: str | None,
) -> tuple[str, tuple[int, np.ndarray[Any, Any]] | None]:  # type: ignore[type-arg]
    """Process multimodal input and return processed text and audio data."""
    processed_text = ""
    audio_input_data: tuple[int, np.ndarray[Any, Any]] | None = None  # type: ignore[type-arg]

    if isinstance(message, dict):
        processed_text = message.get("text", "") or ""
        files = message.get("files", []) or []
        audio_input_data = message.get("audio") or None

        if (files and enable_image_input) or (audio_input_data is not None and enable_audio_input):
            try:
                multimodal_service = get_multimodal_service()
                processed_text = await multimodal_service.process_multimodal_input(
                    processed_text,
                    files=files if enable_image_input else [],
                    audio_input=audio_input_data if enable_audio_input else None,
                    hf_token=token_value,
                    prepend_multimodal=True,
                )
            except Exception as e:
                logger.warning("multimodal_processing_failed", error=str(e))
    else:
        processed_text = str(message) if message else ""

    return processed_text, audio_input_data


async def research_agent(
    message: str | MultimodalPostprocess,
    history: list[dict[str, Any]],
    mode: str = "simple",
    hf_model: str | None = None,
    hf_provider: str | None = None,
    graph_mode: str = "auto",
    use_graph: bool = True,
    enable_image_input: bool = True,
    enable_audio_input: bool = True,
    tts_voice: str = "af_heart",
    tts_speed: float = 1.0,
    web_search_provider: str = "auto",
    oauth_token: gr.OAuthToken | None = None,
    oauth_profile: gr.OAuthProfile | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Main research agent function that processes queries and streams results.

    Args:
        message: User message (text, image, or audio)
        history: Conversation history
        mode: Orchestrator mode
        hf_model: Optional HuggingFace model ID
        hf_provider: Optional inference provider
        graph_mode: Graph execution mode
        use_graph: Whether to use graph execution
        enable_image_input: Whether to process image inputs
        enable_audio_input: Whether to process audio inputs
        tts_voice: TTS voice selection
        tts_speed: TTS speech speed
        web_search_provider: Web search provider selection
        oauth_token: Gradio OAuth token (None if user not logged in)
        oauth_profile: Gradio OAuth profile (None if user not logged in)

    Yields:
        Chat message dictionaries or tuples with audio data
    """
    # Extract OAuth token and username
    token_value = _extract_oauth_token(oauth_token)
    username = _extract_username(oauth_profile)

    # Check if user is logged in (OAuth token or env var)
    # Fallback to env vars for local development or Spaces with HF_TOKEN secret
    has_authentication = bool(
        token_value or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    )

    if not has_authentication:
        yield {
            "role": "assistant",
            "content": (
                "🔐 **Authentication Required**\n\n"
                "Please **sign in with HuggingFace** using the login button at the top of the page "
                "before using this application.\n\n"
                "The login button is required to access the AI models and research tools."
            ),
        }
        return

    # Process multimodal input
    processed_text, audio_input_data = await _process_multimodal_input(
        message, enable_image_input, enable_audio_input, token_value
    )

    if not processed_text.strip():
        yield {
            "role": "assistant",
            "content": "Please enter a research question or provide an image/audio input.",
        }
        return

    # Check available keys (use token_value instead of oauth_token)
    has_huggingface = bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or token_value)

    # Adjust mode if needed
    effective_mode = mode
    if mode == "advanced":
        effective_mode = "simple"

    # Yield authentication and mode status messages
    async for msg in yield_auth_messages(username, token_value, has_huggingface, mode):
        yield msg

    # Run the agent and stream events
    try:
        # use_mock=False - let configure_orchestrator decide based on available keys
        # It will use: OAuth token > Env vars > HF Inference (free tier)
        # Convert empty strings from Textbox to None for defaults
        model_id = hf_model if hf_model and hf_model.strip() else None
        provider_name = hf_provider if hf_provider and hf_provider.strip() else None

        # Log authentication source for debugging
        auth_source = (
            "OAuth"
            if token_value
            else (
                "Env (HF_TOKEN)"
                if os.getenv("HF_TOKEN")
                else ("Env (HUGGINGFACE_API_KEY)" if os.getenv("HUGGINGFACE_API_KEY") else "None")
            )
        )
        logger.info(
            "Configuring orchestrator",
            mode=effective_mode,
            auth_source=auth_source,
            has_oauth_token=bool(token_value),
            model=model_id or "default",
            provider=provider_name or "auto",
        )

        # Convert empty string to None for web_search_provider
        web_search_provider_value = (
            web_search_provider if web_search_provider and web_search_provider.strip() else None
        )

        orchestrator, backend_name = configure_orchestrator(
            use_mock=False,  # Never use mock in production - HF Inference is the free fallback
            mode=effective_mode,
            oauth_token=token_value,  # Use extracted token value - passed to all agents and services
            hf_model=model_id,  # None will use defaults in configure_orchestrator
            hf_provider=provider_name,  # None will use defaults in configure_orchestrator
            graph_mode=graph_mode if graph_mode else None,
            use_graph=use_graph,
            web_search_provider=web_search_provider_value,  # None will use settings default
        )

        yield {
            "role": "assistant",
            "content": f"🔧 **Backend**: {backend_name}\n\nProcessing your query...",
        }

        # Convert history to ModelMessage format if needed
        message_history: list[ModelMessage] = []
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    message_history.append(ModelMessage(role=role, content=content))  # type: ignore[operator]

        # Run orchestrator and stream events
        async for event in orchestrator.run(
            processed_text, message_history=message_history if message_history else None
        ):
            chat_msg = event_to_chat_message(event)
            yield chat_msg

        # Optional: Generate audio output if enabled
        audio_output_data: tuple[int, np.ndarray[Any, Any]] | None = None  # type: ignore[type-arg]
        if settings.enable_audio_output and settings.modal_available:
            try:
                from src.services.tts_modal import get_tts_service

                tts_service = get_tts_service()
                # Get the last message from history for TTS
                last_message = history[-1].get("content", "") if history else processed_text
                if last_message:
                    audio_output_data = await tts_service.synthesize_async(
                        text=last_message,
                        voice=tts_voice,
                        speed=tts_speed,
                    )
            except Exception as e:
                logger.warning("audio_synthesis_failed", error=str(e))
                # Continue without audio output

        # Note: Audio output is handled separately via TTS service
        # Gradio ChatInterface doesn't support tuple yields, so we skip audio output here
        # Audio can be handled via a separate component if needed

    except Exception as e:
        # Return error message without metadata to avoid issues during example caching
        # Metadata can cause validation errors when Gradio caches examples
        # Gradio Chatbot requires plain text - remove all markdown and special characters
        error_msg = str(e).replace("**", "").replace("*", "").replace("`", "")
        # Ensure content is a simple string without any special formatting
        yield {
            "role": "assistant",
            "content": f"Error: {error_msg}. Please check your configuration and try again.",
        }


async def update_model_provider_dropdowns(
    oauth_token: gr.OAuthToken | None = None,
    oauth_profile: gr.OAuthProfile | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Update model and provider dropdowns based on OAuth token.

    This function is called when OAuth token/profile changes (user logs in/out).
    It queries HuggingFace API to get available models and providers.

    Args:
        oauth_token: Gradio OAuth token
        oauth_profile: Gradio OAuth profile

    Returns:
        Tuple of (model_dropdown_update, provider_dropdown_update, status_message)
    """
    from src.utils.hf_model_validator import (
        get_available_models,
        get_available_providers,
        validate_oauth_token,
    )

    # Extract token value
    token_value: str | None = None
    if oauth_token is not None:
        if hasattr(oauth_token, "token"):
            token_value = oauth_token.token
        elif isinstance(oauth_token, str):
            token_value = oauth_token

    # Default values (empty = use default)
    default_models = [""]
    default_providers = [""]
    status_msg = "⚠️ Not authenticated - using default models"

    if not token_value:
        # No token - return defaults
        return (
            gr.update(choices=default_models, value=""),
            gr.update(choices=default_providers, value=""),
            status_msg,
        )

    try:
        # Validate token and get available resources
        validation_result = await validate_oauth_token(token_value)

        if not validation_result["is_valid"]:
            status_msg = (
                f"❌ Token validation failed: {validation_result.get('error', 'Unknown error')}"
            )
            return (
                gr.update(choices=default_models, value=""),
                gr.update(choices=default_providers, value=""),
                status_msg,
            )

        # Get available models and providers
        models = await get_available_models(token=token_value, limit=50)
        providers = await get_available_providers(token=token_value)

        # Combine with defaults
        model_choices = ["", *models[:49]]  # Keep first 49 + empty option
        provider_choices = providers  # Already includes "auto"

        username = validation_result.get("username", "User")

        # Build status message with warning if scope is missing
        scope_warning = ""
        if not validation_result["has_inference_api_scope"]:
            scope_warning = (
                "⚠️ Token may not have 'inference-api' scope - some models may not work\n\n"
            )

        status_msg = (
            f"{scope_warning}✅ Authenticated as {username}\n\n"
            f"📊 Found {len(models)} available models\n"
            f"🔧 Found {len(providers)} available providers"
        )

        logger.info(
            "Updated model/provider dropdowns",
            model_count=len(model_choices),
            provider_count=len(provider_choices),
            username=username,
        )

        return (
            gr.update(choices=model_choices, value=""),
            gr.update(choices=provider_choices, value=""),
            status_msg,
        )

    except Exception as e:
        logger.error("Failed to update dropdowns", error=str(e))
        status_msg = f"⚠️ Failed to load models: {e!s}"
        return (
            gr.update(choices=default_models, value=""),
            gr.update(choices=default_providers, value=""),
            status_msg,
        )


def create_demo() -> gr.Blocks:
    """
    Create the Gradio demo interface with MCP support and OAuth login.

    Returns:
        Configured Gradio Blocks interface with MCP server and OAuth enabled
    """
    with gr.Blocks(title="🔬 The DETERMINATOR", fill_height=True) as demo:
        # Add sidebar with login button and information
        # Reference: Working implementation pattern from Gradio docs
        with gr.Sidebar():
            gr.Markdown("# 🔐 Authentication")
            gr.Markdown(
                "**Sign in with Hugging Face** to access AI models and research tools.\n\n"
                "This application requires authentication to use the inference API."
            )
            gr.LoginButton("Sign in with Hugging Face")
            gr.Markdown("---")
            gr.Markdown("### ℹ️ About")  # noqa: RUF001
            gr.Markdown(
                "**The DETERMINATOR** - Generalist Deep Research Agent\n\n"
                "A powerful research agent that stops at nothing until finding precise answers to complex questions.\n\n"
                "**Available Sources**:\n"
                "- Web Search (general knowledge)\n"
                "- PubMed (biomedical literature)\n"
                "- ClinicalTrials.gov (clinical trials)\n"
                "- Europe PMC (preprints & papers)\n"
                "- RAG (semantic search)\n\n"
                "**Automatic Detection**: Automatically determines if medical knowledge sources are needed for your query.\n\n"
                "⚠️ **Research tool only** - Synthesizes evidence but cannot provide medical advice."
            )
            gr.Markdown("---")

            # Settings Section - Organized in Accordions
            gr.Markdown("## ⚙️ Settings")

            # Research Configuration Accordion
            with gr.Accordion("🔬 Research Configuration", open=True):
                mode_radio = gr.Radio(
                    choices=["simple", "advanced", "iterative", "deep", "auto"],
                    value="simple",
                    label="Orchestrator Mode",
                    info=(
                        "Simple: Linear search-judge loop | "
                        "Advanced: Multi-agent (OpenAI) | "
                        "Iterative: Knowledge-gap driven | "
                        "Deep: Parallel sections | "
                        "Auto: Smart routing"
                    ),
                )

                graph_mode_radio = gr.Radio(
                    choices=["iterative", "deep", "auto"],
                    value="auto",
                    label="Graph Research Mode",
                    info="Iterative: Single loop | Deep: Parallel sections | Auto: Detect from query",
                )

                use_graph_checkbox = gr.Checkbox(
                    value=True,
                    label="Use Graph Execution",
                    info="Enable graph-based workflow execution",
                )

                # Model and Provider selection
                gr.Markdown("### 🤖 Model & Provider")

                # Status message for model/provider loading
                model_provider_status = gr.Markdown(
                    value="⚠️ Sign in to see available models and providers",
                    visible=True,
                )

                # Popular models list (will be updated by validator)
                popular_models = [
                    "",  # Empty = use default
                    "Qwen/Qwen3-Next-80B-A3B-Thinking",
                    "Qwen/Qwen3-235B-A22B-Instruct-2507",
                    "zai-org/GLM-4.5-Air",
                    "meta-llama/Llama-3.1-8B-Instruct",
                    "meta-llama/Llama-3.1-70B-Instruct",
                    "mistralai/Mistral-7B-Instruct-v0.2",
                    "google/gemma-2-9b-it",
                ]

                hf_model_dropdown = gr.Dropdown(
                    choices=popular_models,
                    value="",  # Empty string - will be converted to None in research_agent
                    label="Reasoning Model",
                    info="Select a HuggingFace model (leave empty for default). Sign in to see all available models.",
                    allow_custom_value=True,  # Allow users to type custom model IDs
                )

                # Provider list from README (will be updated by validator)
                providers = [
                    "",  # Empty string = auto-select
                    "nebius",
                    "together",
                    "scaleway",
                    "hyperbolic",
                    "novita",
                    "nscale",
                    "sambanova",
                    "ovh",
                    "fireworks",
                ]

                hf_provider_dropdown = gr.Dropdown(
                    choices=providers,
                    value="",  # Empty string - will be converted to None in research_agent
                    label="Inference Provider",
                    info="Select inference provider (leave empty for auto-select). Sign in to see all available providers.",
                )

                # Web Search Provider selection
                gr.Markdown("### 🔍 Web Search Provider")

                # Available providers with labels indicating availability
                # Format: (display_label, value) - Gradio Dropdown supports tuples
                web_search_provider_options = [
                    ("Auto-detect (Recommended)", "auto"),
                    ("Serper (Google Search + Full Content)", "serper"),
                    ("DuckDuckGo (Free, Snippets Only)", "duckduckgo"),
                    ("SearchXNG (Self-hosted) - Coming Soon", "searchxng"),  # Not fully implemented
                    ("Brave - Coming Soon", "brave"),  # Not implemented
                    ("Tavily - Coming Soon", "tavily"),  # Not implemented
                ]

                # Create Dropdown with label-value pairs
                # Gradio will display labels but return values
                # Disabled options are marked with "Coming Soon" in the label
                # The factory will handle "not implemented" cases gracefully
                web_search_provider_dropdown = gr.Dropdown(
                    choices=web_search_provider_options,
                    value="auto",
                    label="Web Search Provider",
                    info="Select web search provider. 'Auto' detects best available.",
                )

                # Multimodal Input Configuration
                gr.Markdown("### 📷🎤 Multimodal Input")

                enable_image_input_checkbox = gr.Checkbox(
                    value=settings.enable_image_input,
                    label="Enable Image Input (OCR)",
                    info="Process uploaded images with OCR",
                )

                enable_audio_input_checkbox = gr.Checkbox(
                    value=settings.enable_audio_input,
                    label="Enable Audio Input (STT)",
                    info="Process uploaded/recorded audio with speech-to-text",
                )

                # Audio Output Configuration
                gr.Markdown("### 🔊 Audio Output (TTS)")

                enable_audio_output_checkbox = gr.Checkbox(
                    value=settings.enable_audio_output,
                    label="Enable Audio Output",
                    info="Generate audio responses using text-to-speech",
                )

                tts_voice_dropdown = gr.Dropdown(
                    choices=[
                        "af_heart",
                        "af_bella",
                        "af_sarah",
                        "af_sky",
                        "af_nova",
                        "af_shimmer",
                        "af_echo",
                        "af_fable",
                        "af_onyx",
                        "af_angel",
                        "af_asteria",
                        "af_jessica",
                        "af_elli",
                        "af_domi",
                        "af_gigi",
                        "af_freya",
                        "af_glinda",
                        "af_cora",
                        "af_serena",
                        "af_liv",
                        "af_naomi",
                        "af_rachel",
                        "af_antoni",
                        "af_thomas",
                        "af_charlie",
                        "af_emily",
                        "af_george",
                        "af_arnold",
                        "af_adam",
                        "af_sam",
                        "af_paul",
                        "af_josh",
                        "af_daniel",
                        "af_liam",
                        "af_dave",
                        "af_fin",
                        "af_sarah",
                        "af_glinda",
                        "af_grace",
                        "af_dorothy",
                        "af_michael",
                        "af_james",
                        "af_joseph",
                        "af_jeremy",
                        "af_ryan",
                        "af_oliver",
                        "af_harry",
                        "af_kyle",
                        "af_leo",
                        "af_otto",
                        "af_owen",
                        "af_pepper",
                        "af_phil",
                        "af_raven",
                        "af_rocky",
                        "af_rusty",
                        "af_serena",
                        "af_sky",
                        "af_spark",
                        "af_stella",
                        "af_storm",
                        "af_taylor",
                        "af_vera",
                        "af_will",
                        "af_aria",
                        "af_ash",
                        "af_ballad",
                        "af_bella",
                        "af_breeze",
                        "af_cove",
                        "af_dusk",
                        "af_ember",
                        "af_flash",
                        "af_flow",
                        "af_glow",
                        "af_harmony",
                        "af_journey",
                        "af_lullaby",
                        "af_lyra",
                        "af_melody",
                        "af_midnight",
                        "af_moon",
                        "af_muse",
                        "af_music",
                        "af_narrator",
                        "af_nightingale",
                        "af_poet",
                        "af_rain",
                        "af_redwood",
                        "af_rewind",
                        "af_river",
                        "af_sage",
                        "af_seashore",
                        "af_shadow",
                        "af_silver",
                        "af_song",
                        "af_starshine",
                        "af_story",
                        "af_summer",
                        "af_sun",
                        "af_thunder",
                        "af_tide",
                        "af_time",
                        "af_valentino",
                        "af_verdant",
                        "af_verse",
                        "af_vibrant",
                        "af_vivid",
                        "af_warmth",
                        "af_whisper",
                        "af_wilderness",
                        "af_willow",
                        "af_winter",
                        "af_wit",
                        "af_witness",
                        "af_wren",
                        "af_writer",
                        "af_zara",
                        "af_zeus",
                        "af_ziggy",
                        "af_zoom",
                        "af_river",
                        "am_michael",
                        "am_fenrir",
                        "am_puck",
                        "am_echo",
                        "am_eric",
                        "am_liam",
                        "am_onyx",
                        "am_santa",
                        "am_adam",
                    ],
                    value=settings.tts_voice,
                    label="TTS Voice",
                    info="Select TTS voice (American English voices: af_*, am_*)",
                )

                tts_speed_slider = gr.Slider(
                    minimum=0.5,
                    maximum=2.0,
                    value=settings.tts_speed,
                    step=0.1,
                    label="TTS Speech Speed",
                    info="Adjust TTS speech speed (0.5x to 2.0x)",
                )

                gr.Dropdown(
                    choices=["T4", "A10", "A100", "L4", "L40S"],
                    value=settings.tts_gpu or "T4",
                    label="TTS GPU Type",
                    info="Modal GPU type for TTS (T4 is cheapest, A100 is fastest). Note: GPU changes require app restart.",
                    visible=settings.modal_available,
                    interactive=False,  # GPU type set at function definition time, requires restart
                )

                # Audio output component (for TTS response) - moved to sidebar
                audio_output = gr.Audio(
                    label="🔊 Audio Response",
                    visible=settings.enable_audio_output,
                )

        # Update TTS component visibility based on enable_audio_output_checkbox
        # This must be after audio_output is defined
        def update_tts_visibility(
            enabled: bool,
        ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            """Update visibility of TTS components based on enable checkbox."""
            return (
                gr.update(visible=enabled),
                gr.update(visible=enabled),
                gr.update(visible=enabled),
            )

        enable_audio_output_checkbox.change(
            fn=update_tts_visibility,
            inputs=[enable_audio_output_checkbox],
            outputs=[tts_voice_dropdown, tts_speed_slider, audio_output],
        )

        # Update model/provider dropdowns when user clicks refresh button
        # Note: Gradio doesn't directly support watching OAuthToken/OAuthProfile changes
        # So we provide a refresh button that users can click after logging in
        def refresh_models_and_providers(
            oauth_token: gr.OAuthToken | None = None,
            oauth_profile: gr.OAuthProfile | None = None,
        ) -> tuple[dict[str, Any], dict[str, Any], str]:
            """Handle refresh button click and update dropdowns."""
            import asyncio

            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    update_model_provider_dropdowns(oauth_token, oauth_profile)
                )
                return result
            finally:
                loop.close()

        refresh_models_btn = gr.Button(
            value="🔄 Refresh Available Models",
            visible=True,
            size="sm",
        )

        # Note: OAuthToken and OAuthProfile are automatically passed to functions
        # when they are available in the Gradio context
        refresh_models_btn.click(
            fn=refresh_models_and_providers,
            inputs=[],  # OAuth components are automatically available in Gradio context
            outputs=[hf_model_dropdown, hf_provider_dropdown, model_provider_status],
        )

        # Chat interface with multimodal support
        # Examples are provided but will NOT run at startup (cache_examples=False)
        # Users must log in first before using examples or submitting queries
        gr.ChatInterface(
            fn=research_agent,
            multimodal=True,  # Enable multimodal input (text + images + audio)
            title="🔬 The DETERMINATOR",
            description=(
                "*Generalist Deep Research Agent — stops at nothing until finding precise answers to complex questions*\n\n"
                "---\n"
                "**The DETERMINATOR** uses iterative search-and-judge loops to comprehensively investigate any research question. "
                "It automatically determines if medical knowledge sources (PubMed, ClinicalTrials.gov) are needed and adapts its search strategy accordingly.\n\n"
                "**Key Features**:\n"
                "- 🔍 Multi-source search (Web, PubMed, ClinicalTrials.gov, Europe PMC, RAG)\n"
                "- 🧠 Automatic medical knowledge detection\n"
                "- 🔄 Iterative refinement until precise answers are found\n"
                "- ⏹️ Stops only at configured limits (budget, time, iterations)\n"
                "- 📊 Evidence synthesis with citations\n\n"
                "**MCP Server Active**: Connect Claude Desktop to `/gradio_api/mcp/`\n\n"
                "**📷🎤 Multimodal Input Support**:\n"
                "- **Images**: Click the 📷 image icon in the textbox to upload images (OCR)\n"
                "- **Audio**: Click the 🎤 microphone icon in the textbox to record audio (STT)\n"
                "- **Files**: Drag & drop or click to upload image/audio files\n"
                "- **Text**: Type your research questions directly\n\n"
                "💡 **Tip**: Look for the 📷 and 🎤 icons in the text input box below!\n\n"
                "Configure multimodal inputs in the sidebar settings.\n\n"
                "**⚠️ Authentication Required**: Please **sign in with HuggingFace** above before using this application."
            ),
            examples=[
                # When additional_inputs are provided, examples must be lists of lists
                # Each inner list: [message, mode, hf_model, hf_provider, graph_mode, multimodal_enabled]
                # Using actual model IDs and provider names from inference_models.py
                # Note: Provider is optional - if empty, HF will auto-select
                # These examples will NOT run at startup - users must click them after logging in
                # All examples require deep iterative search and information retrieval across multiple sources
                [
                    # Medical research example (only one medical example)
                    "Create a comprehensive report on Long COVID treatments including clinical trials, mechanisms, and safety.",
                    "deep",
                    "zai-org/GLM-4.5-Air",
                    "nebius",
                    "deep",
                    True,
                ],
                [
                    # Technical/Engineering example requiring deep research
                    "Analyze the current state of quantum computing architectures: compare different qubit technologies, error correction methods, and scalability challenges across major platforms including IBM, Google, and IonQ.",
                    "deep",
                    "Qwen/Qwen3-Next-80B-A3B-Thinking",
                    "nebius",
                    "deep",
                    True,
                ],
                [
                    # Historical/Social Science example
                    "Research and synthesize information about the economic impact of the Industrial Revolution on European social structures, including changes in class dynamics, urbanization patterns, and labor movements from 1750-1900.",
                    "deep",
                    "meta-llama/Llama-3.1-70B-Instruct",
                    "together",
                    "deep",
                    True,
                ],
                [
                    # Scientific/Physics example
                    "Investigate the latest developments in fusion energy research: compare ITER, SPARC, and other major projects, analyze recent breakthroughs in plasma confinement, and assess the timeline to commercial fusion power.",
                    "deep",
                    "Qwen/Qwen3-235B-A22B-Instruct-2507",
                    "hyperbolic",
                    "deep",
                    True,
                ],
                [
                    # Technology/Business example
                    "Research the competitive landscape of AI chip manufacturers: analyze NVIDIA, AMD, Intel, and emerging players, compare architectures (GPU vs. TPU vs. NPU), and assess market positioning and future trends.",
                    "deep",
                    "zai-org/GLM-4.5-Air",
                    "fireworks",
                    "deep",
                    True,
                ],
            ],
            additional_inputs=[
                mode_radio,
                hf_model_dropdown,
                hf_provider_dropdown,
                graph_mode_radio,
                use_graph_checkbox,
                enable_image_input_checkbox,
                enable_audio_input_checkbox,
                tts_voice_dropdown,
                tts_speed_slider,
                web_search_provider_dropdown,
                # Note: gr.OAuthToken and gr.OAuthProfile are automatically passed as function parameters
            ],
            cache_examples=False,  # Don't cache examples - requires authentication
        )

    return demo  # type: ignore[no-any-return]


if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)
