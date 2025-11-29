"""Gradio UI for DeepCritical agent with MCP server support."""

import os
from collections.abc import AsyncGenerator
from typing import Any

import gradio as gr
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.huggingface import HuggingFaceProvider

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
) -> tuple[Any, str]:
    """
    Create an orchestrator instance.

    Args:
        use_mock: If True, use MockJudgeHandler (no API key needed)
        mode: Orchestrator mode ("simple" or "advanced")
        oauth_token: Optional OAuth token from HuggingFace login

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
        model: HuggingFaceModel | None = None
        if effective_api_key:
            model_name = settings.huggingface_model or "meta-llama/Llama-3.1-8B-Instruct"
            hf_provider = HuggingFaceProvider(api_key=effective_api_key)
            model = HuggingFaceModel(model_name, provider=hf_provider)
            backend_info = "API (HuggingFace OAuth)"
        else:
            backend_info = "API (Env Config)"

        judge_handler = JudgeHandler(model=model)

    # 3. Free Tier (HuggingFace Inference)
    else:
        judge_handler = HFInferenceJudgeHandler()
        backend_info = "Free Tier (Llama 3.1 / Mistral)"

    orchestrator = create_orchestrator(
        search_handler=search_handler,
        judge_handler=judge_handler,
        config=config,
        mode=mode,  # type: ignore
    )

    return orchestrator, backend_info


def event_to_chat_message(event: AgentEvent) -> gr.ChatMessage:
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
        return gr.ChatMessage(
            role="assistant",
            content=event.message,
        )

    # Build metadata for accordion
    metadata: dict[str, Any] = {}
    if config["title"]:
        metadata["title"] = config["title"]

    # Set status (pending shows spinner, done is collapsed)
    if config["status"] == "pending":
        metadata["status"] = "pending"

    # Add duration if available in data
    if event.data and isinstance(event.data, dict) and "duration" in event.data:
        metadata["duration"] = event.data["duration"]

    # Add log info (iteration number, etc.)
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

    return gr.ChatMessage(
        role="assistant",
        content=event.message,
        metadata=metadata if metadata else None,
    )


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
) -> AsyncGenerator[gr.ChatMessage, None]:
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
        yield gr.ChatMessage(
            role="assistant",
            content=f"👋 **Welcome, {oauth_username}!** Using your HuggingFace account.\n\n",
        )

    # Advanced mode is not supported without OpenAI (which requires manual setup)
    # For now, we only support simple mode with HuggingFace
    if mode == "advanced":
        yield gr.ChatMessage(
            role="assistant",
            content=(
                "⚠️ **Warning**: Advanced mode requires OpenAI API key configuration. "
                "Falling back to simple mode.\n\n"
            ),
        )

    # Inform user about authentication status
    if oauth_token:
        yield gr.ChatMessage(
            role="assistant",
            content=(
                "🔐 **Using HuggingFace OAuth token** - "
                "Authenticated via your HuggingFace account.\n\n"
            ),
        )
    elif not has_huggingface:
        # No keys at all - will use FREE HuggingFace Inference (public models)
        yield gr.ChatMessage(
            role="assistant",
            content=(
                "🤗 **Free Tier**: Using HuggingFace Inference (Llama 3.1 / Mistral) for AI analysis.\n"
                "For premium models or higher rate limits, sign in with HuggingFace above.\n\n"
            ),
        )


async def handle_orchestrator_events(
    orchestrator: Any,
    message: str,
) -> AsyncGenerator[gr.ChatMessage, None]:
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
                    yield gr.ChatMessage(
                        role="assistant",
                        content=content.strip(),
                        metadata={"title": title, "status": "done"},
                    )
                pending_accordions.clear()

            # Yield final response (no accordion for main response)
            yield chat_msg
            continue

        # Handle events with metadata (accordions)
        if chat_msg.metadata:
            title = chat_msg.metadata.get("title")
            status = chat_msg.metadata.get("status")

            if title:
                # For pending operations, accumulate content and show spinner
                if status == "pending":
                    if title not in pending_accordions:
                        pending_accordions[title] = ""
                    pending_accordions[title] += chat_msg.content + "\n"
                    # Yield updated accordion with accumulated content
                    yield gr.ChatMessage(
                        role="assistant",
                        content=pending_accordions[title].strip(),
                        metadata=chat_msg.metadata,
                    )
                elif title in pending_accordions:
                    # Combine pending content with final content
                    final_content = pending_accordions[title] + chat_msg.content
                    del pending_accordions[title]
                    yield gr.ChatMessage(
                        role="assistant",
                        content=final_content.strip(),
                        metadata={"title": title, "status": "done"},
                    )
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
    request: gr.Request | None = None,
) -> AsyncGenerator[gr.ChatMessage | list[gr.ChatMessage], None]:
    """
    Gradio chat function that runs the research agent.

    Args:
        message: User's research question
        history: Chat history (Gradio format)
        mode: Orchestrator mode ("simple" or "advanced")
        request: Gradio request object containing OAuth information

    Yields:
        ChatMessage objects with metadata for accordion display
    """
    if not message.strip():
        yield gr.ChatMessage(
            role="assistant",
            content="Please enter a research question.",
        )
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
        orchestrator, backend_name = configure_orchestrator(
            use_mock=False,  # Never use mock in production - HF Inference is the free fallback
            mode=effective_mode,
            oauth_token=oauth_token,
        )

        yield gr.ChatMessage(
            role="assistant",
            content=f"🧠 **Backend**: {backend_name}\n\n",
        )

        # Handle orchestrator events
        async for msg in handle_orchestrator_events(orchestrator, message):
            yield msg

    except Exception as e:
        yield gr.ChatMessage(
            role="assistant",
            content=f"❌ **Error**: {e!s}",
            metadata={"title": "❌ Error", "status": "done"},
        )


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

        # Chat interface
        gr.ChatInterface(
            fn=research_agent,
            title="🧬 DeepCritical",
            description=(
                "*AI-Powered Drug Repurposing Agent — searches PubMed, "
                "ClinicalTrials.gov & Europe PMC*\n\n"
                "---\n"
                "*Research tool only — not for medical advice.*  \n"
                "**MCP Server Active**: Connect Claude Desktop to `/gradio_api/mcp/`\n\n"
                "**Sign in with HuggingFace** above to use your account's API token automatically."
            ),
            examples=[
                ["What drugs could be repurposed for Alzheimer's disease?", "simple"],
                ["Is metformin effective for treating cancer?", "simple"],
                ["What medications show promise for Long COVID treatment?", "simple"],
            ],
            additional_inputs_accordion=gr.Accordion(label="⚙️ Settings", open=False),
            additional_inputs=[
                gr.Radio(
                    choices=["simple", "advanced"],
                    value="simple",
                    label="Orchestrator Mode",
                    info=(
                        "Simple: Linear (Free Tier Friendly) | Advanced: Multi-Agent (Requires OpenAI - not available without manual config)"
                    ),
                ),
            ],
        )

    return demo


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
