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
    # On HuggingFace Spaces, OAuth token is available via request.oauth_token
    effective_api_key = oauth_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")

    if effective_api_key:
        # We have an API key (OAuth or env) - use pydantic-ai with JudgeHandler
        # This uses HuggingFace's own inference API, not third-party providers
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
                "Please install with: uv add 'pydantic-ai[huggingface]' or use 'openai'/'anthropic' as the LLM provider."
            )
        # Inference API - uses HuggingFace Inference API via AsyncInferenceClient
        # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
        # Create AsyncInferenceClient for inference API
        # AsyncInferenceClient accepts 'token' parameter for API key
        hf_client = AsyncInferenceClient(token=effective_api_key)  # type: ignore[misc]
        # Pass client to HuggingFaceProvider for inference API usage
        provider = HuggingFaceProvider(hf_client=hf_client)  # type: ignore[misc]
        model = HuggingFaceModel(model_name, provider=provider)  # type: ignore[misc]
        backend_info = "API (HuggingFace OAuth)" if oauth_token else "API (Env Config)"

        judge_handler = JudgeHandler(model=model)

    # 3. Free Tier (HuggingFace Inference) - NO API KEY AVAILABLE
    else:
        # No API key available - use HFInferenceJudgeHandler with public models
        # Don't use third-party providers (novita, groq, etc.) as they require their own API keys
        # Use HuggingFace's own inference API with public/ungated models
        # Pass empty provider to use HuggingFace's default (not third-party providers)
        judge_handler = HFInferenceJudgeHandler(
            model_id=hf_model,
            api_key=None,  # No API key - will use public models only
            provider=None,  # Don't specify provider - use HuggingFace's default
        )
        model_display = hf_model.split("/")[-1] if hf_model else "Default (Public Models)"
        backend_info = f"Free Tier ({model_display} - Public Models Only)"

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
    oauth_token: gr.OAuthToken | None = None,
    oauth_profile: gr.OAuthProfile | None = None,
) -> AsyncGenerator[dict[str, Any] | list[dict[str, Any]], None]:
    """
    Gradio chat function that runs the research agent.

    Args:
        message: User's research question
        history: Chat history (Gradio format)
        mode: Orchestrator mode ("simple" or "advanced")
        hf_model: Selected HuggingFace model ID (from dropdown)
        hf_provider: Selected inference provider (from dropdown)
        oauth_token: Gradio OAuth token (None if user not logged in)
        oauth_profile: Gradio OAuth profile (None if user not logged in)

    Yields:
        ChatMessage objects with metadata for accordion display
    """
    # REQUIRE LOGIN BEFORE USE
    # Extract OAuth token and username using Gradio's OAuth types
    # According to Gradio docs: OAuthToken and OAuthProfile are None if user not logged in
    token_value: str | None = None
    username: str | None = None

    if oauth_token is not None:
        # OAuthToken has a .token attribute containing the access token
        token_value = oauth_token.token if hasattr(oauth_token, "token") else None

    if oauth_profile is not None:
        # OAuthProfile has .username, .name, .profile_image attributes
        username = (
            oauth_profile.username
            if hasattr(oauth_profile, "username") and oauth_profile.username
            else (
                oauth_profile.name
                if hasattr(oauth_profile, "name") and oauth_profile.name
                else None
            )
        )

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

    if not message.strip():
        yield {
            "role": "assistant",
            "content": "Please enter a research question.",
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

        orchestrator, backend_name = configure_orchestrator(
            use_mock=False,  # Never use mock in production - HF Inference is the free fallback
            mode=effective_mode,
            oauth_token=token_value,  # Use extracted token value
            hf_model=model_id,  # None will use defaults in configure_orchestrator
            hf_provider=provider_name,  # None will use defaults in configure_orchestrator
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
        # Add login button at the top in a visible Row container
        # LoginButton must be visible and properly configured for OAuth to work
        # Using a Row with scale ensures the button is displayed prominently at the top
        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=200):
                login_btn = gr.LoginButton(
                    value="Sign in with Hugging Face",
                    variant="huggingface",
                    size="lg",
                )

        # Create settings components (hidden - used only for additional_inputs)
        # Model/provider selection removed to avoid dropdown value mismatch errors
        # Settings will use defaults from configure_orchestrator
        with gr.Row(visible=False):
            mode_radio = gr.Radio(
                choices=["simple", "advanced"],
                value="simple",
                label="Orchestrator Mode",
                info="Simple: Linear | Advanced: Multi-Agent (Requires OpenAI)",
            )

            # Hidden text components for model/provider (not dropdowns to avoid value mismatch)
            # These will be empty by default and use defaults in configure_orchestrator
            hf_model_dropdown = gr.Textbox(
                value="",  # Empty string - will be converted to None in research_agent
                label="🤖 Reasoning Model",
                visible=False,  # Hidden from UI
            )

            hf_provider_dropdown = gr.Textbox(
                value="",  # Empty string - will be converted to None in research_agent
                label="⚡ Inference Provider",
                visible=False,  # Hidden from UI
            )

        # Chat interface with model/provider selection
        # Examples are provided but will NOT run at startup (cache_examples=False)
        # Users must log in first before using examples or submitting queries
        gr.ChatInterface(
            fn=research_agent,
            title="🧬 DeepCritical",
            description=(
                "*AI-Powered Drug Repurposing Agent — searches PubMed, "
                "ClinicalTrials.gov & Europe PMC*\n\n"
                "---\n"
                "*Research tool only — not for medical advice.*  \n"
                "**MCP Server Active**: Connect Claude Desktop to `/gradio_api/mcp/`\n\n"
                "**⚠️ Authentication Required**: Please **sign in with HuggingFace** above before using this application."
            ),
            examples=[
                # When additional_inputs are provided, examples must be lists of lists
                # Each inner list: [message, mode, hf_model, hf_provider]
                # Using actual model IDs and provider names from inference_models.py
                # Note: Provider is optional - if empty, HF will auto-select
                # These examples will NOT run at startup - users must click them after logging in
                [
                    "What drugs could be repurposed for Alzheimer's disease?",
                    "simple",
                    "Qwen/Qwen3-Next-80B-A3B-Thinking",
                    "",
                ],
                [
                    "Is metformin effective for treating cancer?",
                    "simple",
                    "Qwen/Qwen3-235B-A22B-Instruct-2507",
                    "",
                ],
                [
                    "What medications show promise for Long COVID treatment?",
                    "simple",
                    "zai-org/GLM-4.5-Air",
                    "nebius",
                ],
            ],
            cache_examples=False,  # CRITICAL: Disable example caching to prevent examples from running at startup
            # Examples will only run when user explicitly clicks them (after login)
            additional_inputs_accordion=gr.Accordion(label="⚙️ Settings", open=True, visible=True),
            additional_inputs=[
                mode_radio,
                hf_model_dropdown,
                hf_provider_dropdown,
                # Note: gr.OAuthToken and gr.OAuthProfile are automatically passed as function parameters
                # when user is logged in - they should NOT be added to additional_inputs
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
