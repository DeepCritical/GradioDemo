"""Gradio UI for DeepCritical agent with MCP server support."""

import os
from collections.abc import AsyncGenerator
from typing import Any

import gradio as gr

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

    _HUGGINGFACE_AVAILABLE = True
except ImportError:
    HuggingFaceModel = None  # type: ignore[assignment, misc]
    HuggingFaceProvider = None  # type: ignore[assignment, misc]
    AsyncInferenceClient = None  # type: ignore[assignment, misc]
    _HUGGINGFACE_AVAILABLE = False

from src.agent_factory.judges import HFInferenceJudgeHandler, JudgeHandler, MockJudgeHandler
from src.orchestrator_factory import create_orchestrator
from src.tools.clinicaltrials import ClinicalTrialsTool
from src.tools.europepmc import EuropePMCTool
from src.tools.pubmed import PubMedTool
from src.tools.search_handler import SearchHandler
from src.utils.config import settings
from src.utils.inference_models import get_available_models, get_available_providers
from src.utils.models import AgentEvent, OrchestratorConfig


def configure_orchestrator(
    use_mock: bool = False,
    mode: str = "simple",
    oauth_token: str | None = None,
    hf_model: str | None = None,
    hf_provider: str | None = None,
) -> tuple[Any, str]:
    """
    Create an orchestrator instance.

    Args:
        use_mock: If True, use MockJudgeHandler (no API key needed)
        mode: Orchestrator mode ("simple" or "advanced")
        oauth_token: Optional OAuth token from HuggingFace login
        hf_model: Selected HuggingFace model ID
        hf_provider: Selected inference provider

    Returns:
        Tuple of (Orchestrator instance, backend_name)
    """
    # Create orchestrator config
    config = OrchestratorConfig(
        max_iterations=10,
        max_results_per_tool=10,
    )

    # Create search tools
    search_handler = SearchHandler(
        tools=[PubMedTool(), ClinicalTrialsTool(), EuropePMCTool()],
        timeout=config.search_timeout,
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
    effective_api_key = oauth_token
    if effective_api_key or (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")):
        model: Any | None = None
        if effective_api_key:
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
                    "Please install with: uv add 'pydantic-ai[huggingface]' or use 'openai'/'anthropic' as the LLM provider."
                )
            # Inference API - uses HuggingFace Inference API via AsyncInferenceClient
            # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
            # Create AsyncInferenceClient for inference API
            hf_client = AsyncInferenceClient(api_key=effective_api_key)  # type: ignore[misc]
            # Pass client to HuggingFaceProvider for inference API usage
            provider = HuggingFaceProvider(hf_client=hf_client)  # type: ignore[misc]
            model = HuggingFaceModel(model_name, provider=provider)  # type: ignore[misc]
            backend_info = "API (HuggingFace OAuth)"
        else:
            backend_info = "API (Env Config)"

        judge_handler = JudgeHandler(model=model)

    # 3. Free Tier (HuggingFace Inference)
    else:
        # Pass OAuth token if available (even if not in env vars)
        # This allows OAuth login to work with free tier models
        # Use selected model and provider if provided
        judge_handler = HFInferenceJudgeHandler(
            model_id=hf_model,
            api_key=oauth_token,
            provider=hf_provider,
        )
        model_display = hf_model.split("/")[-1] if hf_model else "Default"
        provider_display = hf_provider or "auto"
        backend_info = f"Free Tier ({model_display} via {provider_display})" + (
            " (OAuth)" if oauth_token else ""
        )

    orchestrator = create_orchestrator(
        search_handler=search_handler,
        judge_handler=judge_handler,
        config=config,
        mode=mode,  # type: ignore
    )

    return orchestrator, backend_info


def event_to_chat_message(event: AgentEvent) -> dict[str, Any]:
    """
    Convert AgentEvent to gr.ChatMessage with metadata for accordion display.

    Args:
        event: The AgentEvent to convert

    Returns:
        ChatMessage with metadata for collapsible accordion
    """
    # Map event types to accordion titles and determine if pending
    event_configs: dict[str, dict[str, Any]] = {
        "started": {"title": "🚀 Starting Research", "status": "done", "icon": "🚀"},
        "searching": {"title": "🔍 Searching Literature", "status": "pending", "icon": "🔍"},
        "search_complete": {"title": "📚 Search Results", "status": "done", "icon": "📚"},
        "judging": {"title": "🧠 Evaluating Evidence", "status": "pending", "icon": "🧠"},
        "judge_complete": {"title": "✅ Evidence Assessment", "status": "done", "icon": "✅"},
        "looping": {"title": "🔄 Research Iteration", "status": "pending", "icon": "🔄"},
        "synthesizing": {"title": "📝 Synthesizing Report", "status": "pending", "icon": "📝"},
        "hypothesizing": {"title": "🔬 Generating Hypothesis", "status": "pending", "icon": "🔬"},
        "analyzing": {"title": "📊 Statistical Analysis", "status": "pending", "icon": "📊"},
        "analysis_complete": {"title": "📈 Analysis Results", "status": "done", "icon": "📈"},
        "streaming": {"title": "📡 Processing", "status": "pending", "icon": "📡"},
        "complete": {"title": None, "status": "done", "icon": "🎉"},  # Main response, no accordion
        "error": {"title": "❌ Error", "status": "done", "icon": "❌"},
    }

    config = event_configs.get(
        event.type, {"title": f"• {event.type}", "status": "done", "icon": "•"}
    )

    # For complete events, return main response without accordion
    if event.type == "complete":
        # Return as dict format for Gradio Chatbot compatibility
        return {
            "role": "assistant",
            "content": event.message,
        }

    # Build metadata for accordion according to Gradio ChatMessage spec
    # Metadata keys: title (str), status ("pending"|"done"), log (str), duration (float)
    # See: https://www.gradio.app/guides/agents-and-tool-usage
    metadata: dict[str, Any] = {}

    # Title is required for accordion display - must be string
    if config["title"]:
        metadata["title"] = str(config["title"])

    # Set status (pending shows spinner, done is collapsed)
    # Must be exactly "pending" or "done" per Gradio spec
    if config["status"] == "pending":
        metadata["status"] = "pending"
    elif config["status"] == "done":
        metadata["status"] = "done"

    # Add duration if available in data (must be float)
    if event.data and isinstance(event.data, dict) and "duration" in event.data:
        duration = event.data["duration"]
        if isinstance(duration, int | float):
            metadata["duration"] = float(duration)

    # Add log info (iteration number, etc.) - must be string
    log_parts: list[str] = []
    if event.iteration > 0:
        log_parts.append(f"Iteration {event.iteration}")
    if event.data and isinstance(event.data, dict):
        if "tool" in event.data:
            log_parts.append(f"Tool: {event.data['tool']}")
        if "results_count" in event.data:
            log_parts.append(f"Results: {event.data['results_count']}")
    if log_parts:
        metadata["log"] = " | ".join(log_parts)

    # Return as dict format for Gradio Chatbot compatibility
    # According to Gradio docs: https://www.gradio.app/guides/agents-and-tool-usage
    # ChatMessage format: {"role": "assistant", "content": "...", "metadata": {...}}
    # Metadata must have "title" key for accordion display
    # Valid metadata keys: title (str), status ("pending"|"done"), log (str), duration (float)
    result: dict[str, Any] = {
        "role": "assistant",
        "content": event.message,
    }
    # Only add metadata if it has a title (required for accordion display)
    # Ensure metadata values match Gradio's expected types
    if metadata and metadata.get("title"):
        # Ensure status is valid if present
        if "status" in metadata:
            status = metadata["status"]
            if status not in ("pending", "done"):
                metadata["status"] = "done"  # Default to "done" if invalid
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
        if hasattr(request.oauth_profile, "username"):
            oauth_username = request.oauth_profile.username
        elif hasattr(request.oauth_profile, "name"):
            oauth_username = request.oauth_profile.name

    return oauth_token, oauth_username


async def yield_auth_messages(
    oauth_username: str | None,
    oauth_token: str | None,
    has_huggingface: bool,
    mode: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Yield authentication and mode status messages.

    Args:
        oauth_username: OAuth username if available
        oauth_token: OAuth token if available
        has_huggingface: Whether HuggingFace credentials are available
        mode: Orchestrator mode

    Yields:
        ChatMessage objects with authentication status
    """
    # Show user greeting if logged in via OAuth
    if oauth_username:
        yield {
            "role": "assistant",
            "content": f"👋 **Welcome, {oauth_username}!** Using your HuggingFace account.\n\n",
        }

    # Advanced mode is not supported without OpenAI (which requires manual setup)
    # For now, we only support simple mode with HuggingFace
    if mode == "advanced":
        yield {
            "role": "assistant",
            "content": (
                "⚠️ **Warning**: Advanced mode requires OpenAI API key configuration. "
                "Falling back to simple mode.\n\n"
            ),
        }

    # Inform user about authentication status
    if oauth_token:
        yield {
            "role": "assistant",
            "content": (
                "🔐 **Using HuggingFace OAuth token** - "
                "Authenticated via your HuggingFace account.\n\n"
            ),
        }
    elif not has_huggingface:
        # No keys at all - will use FREE HuggingFace Inference (public models)
        yield {
            "role": "assistant",
            "content": (
                "🤗 **Free Tier**: Using HuggingFace Inference (Llama 3.1 / Mistral) for AI analysis.\n"
                "For premium models or higher rate limits, sign in with HuggingFace above.\n\n"
            ),
        }


async def handle_orchestrator_events(
    orchestrator: Any,
    message: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Handle orchestrator events and yield ChatMessages.

    Args:
        orchestrator: The orchestrator instance
        message: The research question

    Yields:
        ChatMessage objects from orchestrator events
    """
    # Track pending accordions for real-time updates
    pending_accordions: dict[str, str] = {}  # title -> accumulated content

    async for event in orchestrator.run(message):
        # Convert event to ChatMessage with metadata
        chat_msg = event_to_chat_message(event)

        # Handle complete events (main response)
        if event.type == "complete":
            # Close any pending accordions first
            if pending_accordions:
                for title, content in pending_accordions.items():
                    yield {
                        "role": "assistant",
                        "content": content.strip(),
                        "metadata": {"title": title, "status": "done"},
                    }
                pending_accordions.clear()

            # Yield final response (no accordion for main response)
            # chat_msg is already a dict from event_to_chat_message
            yield chat_msg
            continue

        # Handle events with metadata (accordions)
        # chat_msg is always a dict from event_to_chat_message
        metadata: dict[str, Any] = chat_msg.get("metadata", {})
        if metadata:
            msg_title: str | None = metadata.get("title")
            msg_status: str | None = metadata.get("status")

            if msg_title:
                # For pending operations, accumulate content and show spinner
                if msg_status == "pending":
                    if msg_title not in pending_accordions:
                        pending_accordions[msg_title] = ""
                    # chat_msg is always a dict, so access content via key
                    content = chat_msg.get("content", "")
                    pending_accordions[msg_title] += content + "\n"
                    # Yield updated accordion with accumulated content
                    yield {
                        "role": "assistant",
                        "content": pending_accordions[msg_title].strip(),
                        "metadata": chat_msg.get("metadata", {}),
                    }
                elif msg_title in pending_accordions:
                    # Combine pending content with final content
                    # chat_msg is always a dict, so access content via key
                    content = chat_msg.get("content", "")
                    final_content = pending_accordions[msg_title] + content
                    del pending_accordions[msg_title]
                    yield {
                        "role": "assistant",
                        "content": final_content.strip(),
                        "metadata": {"title": msg_title, "status": "done"},
                    }
                else:
                    # New done accordion (no pending state)
                    yield chat_msg
            else:
                # No title, yield as-is
                yield chat_msg
        else:
            # No metadata, yield as plain message
            yield chat_msg


async def research_agent(
    message: str,
    history: list[dict[str, Any]],
    mode: str = "simple",
    hf_model: str | None = None,
    hf_provider: str | None = None,
    request: gr.Request | None = None,
) -> AsyncGenerator[dict[str, Any] | list[dict[str, Any]], None]:
    """
    Gradio chat function that runs the research agent.

    Args:
        message: User's research question
        history: Chat history (Gradio format)
        mode: Orchestrator mode ("simple" or "advanced")
        hf_model: Selected HuggingFace model ID (from dropdown)
        hf_provider: Selected inference provider (from dropdown)
        request: Gradio request object containing OAuth information

    Yields:
        ChatMessage objects with metadata for accordion display
    """
    if not message.strip():
        yield {
            "role": "assistant",
            "content": "Please enter a research question.",
        }
        return

    # Extract OAuth token from request if available
    oauth_token, oauth_username = extract_oauth_info(request)

    # Check available keys
    has_huggingface = bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or oauth_token)

    # Adjust mode if needed
    effective_mode = mode
    if mode == "advanced":
        effective_mode = "simple"

    # Yield authentication and mode status messages
    async for msg in yield_auth_messages(oauth_username, oauth_token, has_huggingface, mode):
        yield msg

    # Run the agent and stream events
    try:
        # use_mock=False - let configure_orchestrator decide based on available keys
        # It will use: OAuth token > Env vars > HF Inference (free tier)
        # hf_model and hf_provider come from dropdown, so they're guaranteed to be valid
        orchestrator, backend_name = configure_orchestrator(
            use_mock=False,  # Never use mock in production - HF Inference is the free fallback
            mode=effective_mode,
            oauth_token=oauth_token,
            hf_model=hf_model,  # Can be None, will use defaults in configure_orchestrator
            hf_provider=hf_provider,  # Can be None, will use defaults in configure_orchestrator
        )

        yield {
            "role": "assistant",
            "content": f"🧠 **Backend**: {backend_name}\n\n",
        }

        # Handle orchestrator events
        async for msg in handle_orchestrator_events(orchestrator, message):
            yield msg

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


def create_demo() -> gr.Blocks:
    """
    Create the Gradio demo interface with MCP support and OAuth login.

    Returns:
        Configured Gradio Blocks interface with MCP server and OAuth enabled
    """
    with gr.Blocks(title="🧬 DeepCritical") as demo:
        # Add login button at the top
        with gr.Row():
            gr.LoginButton()

        # Get initial model/provider lists (no auth by default)
        # Check if user has auth to determine which model list to use
        has_auth = bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY"))

        # Get the appropriate model list based on user's actual auth status
        # CRITICAL: Use the list that matches the user's auth status to avoid mismatches
        if has_auth:
            # User has auth - get models available with auth (includes gated models)
            initial_models = get_available_models(has_auth=True)
            # Fallback to unauthenticated models if auth list is empty (shouldn't happen, but be safe)
            if not initial_models:
                initial_models = get_available_models(has_auth=False)
        else:
            # User doesn't have auth - only get unauthenticated models (ungated only)
            initial_models = get_available_models(has_auth=False)

        # Extract available model IDs (first element of tuples) - this is what Gradio uses as values
        available_model_ids = [m[0] for m in initial_models] if initial_models else []

        # Prefer latest reasoning models if available, otherwise use fallback
        preferred_models = [
            "Qwen/Qwen3-Next-80B-A3B-Thinking",
            "Qwen/Qwen3-Next-80B-A3B-Instruct",
            "meta-llama/Llama-3.3-70B-Instruct",
        ]

        # Find first available preferred model from the actual available models list
        # CRITICAL: Only use models that are actually in available_model_ids
        initial_model_id = None
        for preferred in preferred_models:
            if preferred in available_model_ids:
                initial_model_id = preferred
                break

        # Fall back to first available model from the actual list
        # CRITICAL: Always use a model that's guaranteed to be in available_model_ids
        if not initial_model_id:
            if available_model_ids:
                initial_model_id = available_model_ids[0]  # First model ID from available list
            else:
                # No models available - this shouldn't happen, but handle gracefully
                initial_model_id = None

        # Final safety check: ensure initial_model_id is actually in the available models
        # This is the last line of defense - if it's not in the list, use the first available
        if initial_model_id and initial_model_id not in available_model_ids:
            if available_model_ids:
                initial_model_id = available_model_ids[0]
            else:
                initial_model_id = None

        # Get providers for the selected model (only if we have a valid model)
        # CRITICAL: Re-validate model_id is still in available models before getting providers
        initial_providers = []
        initial_provider = None
        if initial_model_id and initial_model_id in available_model_ids:
            initial_providers = get_available_providers(initial_model_id, has_auth=has_auth)
            # Ensure we have a valid provider value that's in the choices
            if initial_providers:
                available_provider_ids = [p[0] for p in initial_providers]
                if available_provider_ids:
                    initial_provider = available_provider_ids[0]  # Use first provider's ID
                else:
                    initial_provider = None
            else:
                initial_provider = None
        else:
            # Model not available - reset to None
            initial_model_id = None
            initial_provider = None

        # Create dropdowns for model and provider selection
        # Note: Components can be in a hidden row and still work with ChatInterface additional_inputs
        # The visible=False just hides the row itself, but components are still accessible
        with gr.Row(visible=False):
            mode_radio = gr.Radio(
                choices=["simple", "advanced"],
                value="simple",
                label="Orchestrator Mode",
                info="Simple: Linear | Advanced: Multi-Agent (Requires OpenAI)",
            )

            # Final validation: ensure value is in choices before creating dropdown
            # Gradio requires the value to be exactly one of the choice values (first element of tuples)
            # CRITICAL: Always default to the first available choice to ensure value is always valid
            # Extract model IDs from choices (first element of each tuple) - do this fresh right before creating dropdown
            model_ids_in_choices = [m[0] for m in initial_models] if initial_models else []

            # Determine the model value - must be in model_ids_in_choices
            # CRITICAL: Only use values that are actually in the current choices list
            model_value = None
            if initial_models and model_ids_in_choices:
                # First try to use initial_model_id if it's valid and in the current choices
                if initial_model_id and initial_model_id in model_ids_in_choices:
                    model_value = initial_model_id
                else:
                    # Fallback to first available model - guarantees a valid value
                    model_value = model_ids_in_choices[0]

            # Absolute final check: if we have choices but model_value is None or invalid, use first choice
            # This is the last line of defense - ensure value is ALWAYS valid
            if initial_models and model_ids_in_choices:
                if not model_value or model_value not in model_ids_in_choices:
                    model_value = model_ids_in_choices[0]
            elif not initial_models:
                # No models available - set to None (empty dropdown)
                model_value = None

            # CRITICAL: Only set value if it's actually in the choices list
            # This prevents Gradio warnings about invalid values
            final_model_value = None
            if model_value and initial_models:
                # Double-check the value is in the choices (defensive programming)
                if model_value in model_ids_in_choices:
                    final_model_value = model_value
                elif model_ids_in_choices:
                    # If value is invalid, use first available
                    final_model_value = model_ids_in_choices[0]

            hf_model_dropdown = gr.Dropdown(
                choices=initial_models if initial_models else [],
                value=final_model_value,  # Only set if validated to be in choices
                label="🤖 Reasoning Model",
                info="Select AI model for evidence assessment. Sign in to access gated models.",
                interactive=True,
                allow_custom_value=False,  # Only allow values from choices
            )

            # Final validation for provider: ensure value is in choices
            # CRITICAL: Always default to the first available choice to ensure value is always valid
            # Extract provider IDs fresh right before creating dropdown
            provider_ids_in_choices = [p[0] for p in initial_providers] if initial_providers else []
            provider_value = None

            # CRITICAL: Only use values that are actually in the current choices list
            if initial_providers and provider_ids_in_choices:
                # First try to use the preferred provider if it's available and in current choices
                if initial_provider and initial_provider in provider_ids_in_choices:
                    provider_value = initial_provider
                else:
                    # Fallback to first available provider - this ensures we always have a valid value
                    provider_value = provider_ids_in_choices[0]

            # Absolute final check: if we have choices but provider_value is None or invalid, use first choice
            # This is the last line of defense - ensure value is ALWAYS valid
            if initial_providers and provider_ids_in_choices:
                if not provider_value or provider_value not in provider_ids_in_choices:
                    provider_value = provider_ids_in_choices[0]
            elif not initial_providers:
                # No providers available - set to None (empty dropdown)
                provider_value = None

            # CRITICAL: Only set value if it's actually in the choices list
            # This prevents Gradio warnings about invalid values
            final_provider_value = None
            if provider_value and initial_providers:
                # Double-check the value is in the choices (defensive programming)
                if provider_value in provider_ids_in_choices:
                    final_provider_value = provider_value
                elif provider_ids_in_choices:
                    # If value is invalid, use first available
                    final_provider_value = provider_ids_in_choices[0]

            hf_provider_dropdown = gr.Dropdown(
                choices=initial_providers if initial_providers else [],
                value=final_provider_value,  # Only set if validated to be in choices
                label="⚡ Inference Provider",
                info="Select provider for model execution. Some require authentication.",
                interactive=True,
                allow_custom_value=False,  # Only allow values from choices
            )

        # Update providers when model changes
        def update_providers(model_id: str, request: gr.Request | None = None) -> gr.Dropdown:
            """Update provider list when model changes."""
            # Check if user is authenticated
            oauth_token, _ = extract_oauth_info(request)
            has_auth = bool(
                oauth_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
            )

            providers = get_available_providers(model_id, has_auth=has_auth)
            if providers:
                # Always set value to first provider to ensure it's valid
                return gr.Dropdown(choices=providers, value=providers[0][0])
            # If no providers, return empty dropdown with no value
            return gr.Dropdown(choices=[], value=None)

        hf_model_dropdown.change(
            fn=update_providers,
            inputs=[hf_model_dropdown],
            outputs=[hf_provider_dropdown],
        )

        # Chat interface with model/provider selection
        gr.ChatInterface(
            fn=research_agent,
            title="🧬 DeepCritical",
            description=(
                "*AI-Powered Drug Repurposing Agent — searches PubMed, "
                "ClinicalTrials.gov & Europe PMC*\n\n"
                "---\n"
                "*Research tool only — not for medical advice.*  \n"
                "**MCP Server Active**: Connect Claude Desktop to `/gradio_api/mcp/`\n\n"
                "**Sign in with HuggingFace** above to access premium models and providers."
            ),
            examples=[
                # When additional_inputs are provided, examples must be lists of lists
                # Each inner list: [message, mode, hf_model, hf_provider]
                # Disabled example caching to avoid startup errors - examples still work but won't be pre-cached
                [
                    "What drugs could be repurposed for Alzheimer's disease?",
                    "simple",
                    None,
                    None,
                ],
                ["Is metformin effective for treating cancer?", "simple", None, None],
                [
                    "What medications show promise for Long COVID treatment?",
                    "simple",
                    None,
                    None,
                ],
            ],
            cache_examples=False,  # Disable example caching to prevent startup errors
            additional_inputs_accordion=gr.Accordion(label="⚙️ Settings", open=False),
            additional_inputs=[
                mode_radio,
                hf_model_dropdown,
                hf_provider_dropdown,
            ],
        )

    return demo  # type: ignore[no-any-return]


def main() -> None:
    """Run the Gradio app with MCP server enabled."""
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        mcp_server=True,
        ssr_mode=False,  # Fix for intermittent loading/hydration issues in HF Spaces
    )


if __name__ == "__main__":
    main()
