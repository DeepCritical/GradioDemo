"""Gradio UI for The DETERMINATOR agent with MCP server support."""

import os
from collections.abc import AsyncGenerator
from typing import Any

import gradio as gr
import numpy as np
from gradio.components.multimodal_textbox import MultimodalPostprocess

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
from src.services.audio_processing import get_audio_service
from src.services.multimodal_processing import get_multimodal_service
import structlog
from src.tools.clinicaltrials import ClinicalTrialsTool
from src.tools.europepmc import EuropePMCTool
from src.tools.pubmed import PubMedTool
from src.tools.search_handler import SearchHandler
from src.tools.neo4j_search import Neo4jSearchTool
from src.utils.config import settings
from src.utils.models import AgentEvent, OrchestratorConfig

logger = structlog.get_logger()


def configure_orchestrator(
    use_mock: bool = False,
    mode: str = "simple",
    oauth_token: str | None = None,
    hf_model: str | None = None,
    hf_provider: str | None = None,
    graph_mode: str | None = None,
    use_graph: bool = True,
) -> tuple[Any, str]:
    """
    Create an orchestrator instance.

    Args:
        use_mock: If True, use MockJudgeHandler (no API key needed)
        mode: Orchestrator mode ("simple", "advanced", "iterative", "deep", or "auto")
        oauth_token: Optional OAuth token from HuggingFace login
        hf_model: Selected HuggingFace model ID
        hf_provider: Selected inference provider
        graph_mode: Graph research mode ("iterative", "deep", or "auto") - used when mode is graph-based
        use_graph: Whether to use graph execution (True) or agent chains (False)

    Returns:
        Tuple of (Orchestrator instance, backend_name)
    """
    # Create orchestrator config
    config = OrchestratorConfig(
        max_iterations=10,
        max_results_per_tool=10,
    )

    # Create search tools with RAG enabled
    # Pass OAuth token to SearchHandler so it can be used by RAG service
    tools = [Neo4jSearchTool(),PubMedTool(), ClinicalTrialsTool(), EuropePMCTool()]

    # Add web search tool if available
    from src.tools.web_search_factory import create_web_search_tool

    web_search_tool = create_web_search_tool()
    if web_search_tool is not None:
        tools.append(web_search_tool)
        logger.info("Web search tool added to search handler", provider=web_search_tool.name)

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
                "Please install with: uv add 'pydantic-ai[huggingface]' to use HuggingFace inference providers."
            )
        # Inference API - uses HuggingFace Inference API
        # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
        # HuggingFaceProvider accepts api_key parameter directly
        # This is consistent with usage in src/utils/llm_factory.py and src/agent_factory/judges.py
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
    import os
    # Check for common file extensions
    file_extensions = ['.md', '.pdf', '.txt', '.json', '.csv', '.xlsx', '.docx', '.html']
    text_lower = text.lower().strip()

    # Check if it ends with a file extension
    if any(text_lower.endswith(ext) for ext in file_extensions):
        # Check if it's a valid path (absolute or relative)
        if os.path.sep in text or '/' in text or '\\' in text:
            return True
        # Or if it's just a filename with extension
        if '.' in text and len(text.split('.')) == 2:
            return True

    # Check if it's an absolute path
    if os.path.isabs(text):
        return True

    return False


def _get_file_name(file_path: str) -> str:
    """Extract filename from file path.

    Args:
        file_path: Path to extract filename from

    Returns:
        Filename without directory path
    """
    import os
    return os.path.basename(file_path)


def _process_multimodal_input(message: MultimodalPostprocess | str | None) -> tuple[str, dict[str, Any]]:
    """Process multimodal input into text and context metadata.

    Args:
        message: Multimodal message object from Gradio or plain string

    Returns:
        Tuple of (text_content, context_data) where context_data includes file info
    """
    context: dict[str, Any] = {"files": []}

    if message is None:
        return "", context

    # If message is a plain string, return it directly
    if isinstance(message, str):
        return message, context

    # Multimodal message structure:
    # {
    #   "text": "user text",
    #   "files": [
    #     {"path": "...", "type": "image", "size": 12345},
    #     {"path": "...", "type": "audio", "size": 54321}
    #   ]
    # }
    text_content = message.get("text", "") if isinstance(message, dict) else ""
    files = message.get("files", []) if isinstance(message, dict) else []

    # Process attached files
    for file_info in files:
        if not isinstance(file_info, dict):
            continue

        file_path = file_info.get("path")
        if not file_path:
            continue

        # Only include files that exist
        if not os.path.exists(file_path):
            continue

        file_name = _get_file_name(file_path)
        file_type = file_info.get("type", "unknown")
        file_size = os.path.getsize(file_path)

        context["files"].append(
            {
                "path": file_path,
                "name": file_name,
                "type": file_type,
                "size": file_size,
            }
        )

    return text_content, context


def _is_supported_file(file_path: str) -> bool:
    """Check if file type is supported for processing.

    Args:
        file_path: Path to check

    Returns:
        True if file type is supported
    """
    supported_extensions = {
        "image": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"},
        "audio": {".wav", ".mp3", ".ogg", ".flac", ".m4a"},
        "text": {".txt", ".md", ".pdf", ".doc", ".docx"},
    }

    file_ext = os.path.splitext(file_path)[1].lower()
    return any(file_ext in exts for exts in supported_extensions.values())


def _process_attached_files(files: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Process attached files and route to appropriate services.

    Args:
        files: List of file info dictionaries

    Returns:
        Tuple of (context_files, processed_results)
    """
    context_files = []
    processed_results = []

    for file_info in files:
        file_path = file_info.get("path")
        file_type = file_info.get("type", "unknown")

        if not file_path or not os.path.exists(file_path):
            continue

        if not _is_supported_file(file_path):
            logger.warning("unsupported_file_type", file_path=file_path, file_type=file_type)
            continue

        context_files.append(
            {
                "path": file_path,
                "name": _get_file_name(file_path),
                "type": file_type,
                "size": os.path.getsize(file_path),
            }
        )

        # Route to appropriate processing service
        try:
            if file_type == "image" and settings.enable_image_input:
                multimodal_service = get_multimodal_service()
                image_text = multimodal_service.extract_text_from_image(file_path)
                if image_text:
                    processed_results.append(
                        {
                            "type": "image_text",
                            "file": file_path,
                            "content": image_text,
                        }
                    )
            elif file_type == "audio" and settings.enable_audio_input:
                multimodal_service = get_multimodal_service()
                audio_text = multimodal_service.transcribe_audio(file_path)
                if audio_text:
                    processed_results.append(
                        {
                            "type": "audio_text",
                            "file": file_path,
                            "content": audio_text,
                        }
                    )
        except Exception as e:
            logger.warning(
                "file_processing_failed", file_path=file_path, file_type=file_type, error=str(e)
            )

    return context_files, processed_results


def configure_audio_tts() -> tuple[str, float, str, str, str]:
    """Get TTS configuration values with safe defaults.

    Returns:
        Tuple of (voice, speed, gpu, region, environment)
    """
    return (
        getattr(settings, "tts_voice", "af_heart"),
        getattr(settings, "tts_speed", 1.0),
        getattr(settings, "tts_gpu", "T4"),
        getattr(settings, "tts_region", "us-east-1"),
        getattr(settings, "tts_environment", "prod"),
    )


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
    graph_mode: str | None = None,
    use_graph: bool = True,
    request: gr.Request | None = None,
    enable_image_input: bool = False,
    enable_audio_input: bool = False,
    tts_voice: str | None = None,
    tts_speed: float | None = None,
) -> AsyncGenerator[dict[str, Any] | list[dict[str, Any]] | tuple[Any, Any], None]:
    """
    Gradio chat function that runs the research agent.

    Args:
        message: User's research question
        history: Chat history (Gradio format)
        mode: Orchestrator mode ("simple" or "advanced")
        hf_model: Selected HuggingFace model ID (from dropdown)
        hf_provider: Selected inference provider (from dropdown)
        graph_mode: Graph research mode ("iterative", "deep", or "auto")
        use_graph: Whether to use graph execution (True) or agent chains (False)
        request: Gradio request object containing OAuth information
        enable_image_input: Whether to allow image input processing
        enable_audio_input: Whether to allow audio input processing
        tts_voice: Optional override for TTS voice
        tts_speed: Optional override for TTS speed

    Yields:
        ChatMessage objects with metadata for accordion display, optionally with audio output
    """
    if not message:
        yield {
            "role": "assistant",
            "content": "Please enter a research question.",
        }, None
        return

    # Extract OAuth token from request if available
    oauth_token, oauth_username = extract_oauth_info(request)

    # Check available keys
    has_huggingface = bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or oauth_token)

    # Adjust mode if needed
    effective_mode = mode
    if mode == "advanced":
        effective_mode = "simple"

    # Process multimodal input and context
    processed_text = message
    multimodal_context: dict[str, Any] = {}
    files_results: list[dict[str, Any]] = []

    if isinstance(message, dict):  # MultimodalPostprocess is a dict-like structure
        processed_text, multimodal_context = _process_multimodal_input(message)
        # Combine text from processed files into the main message
        files_context, files_results = _process_attached_files(multimodal_context.get("files", []))
        multimodal_context["files"] = files_context
        for result in files_results:
            if "content" in result:
                processed_text += f"\n\n{result['type']} from {result['file']}:\n{result['content']}"

    # Include multimodal context in the initial message
    if multimodal_context:
        processed_text += "\n\nAttached Files:\n"
        for file_info in multimodal_context["files"]:
            processed_text += f"- {file_info['name']} ({file_info['type']}, {file_info['size']} bytes)\n"

    # Yield authentication and mode status messages
    async for msg in yield_auth_messages(oauth_username, oauth_token, has_huggingface, mode):
        yield msg, None

    # Run the agent and stream events
    try:
        # use_mock=False - let configure_orchestrator decide based on available keys
        # It will use: OAuth token > Env vars > HF Inference (free tier)
        # hf_model and hf_provider come from dropdown, so they're guaranteed to be valid
        orchestrator, backend_name = configure_orchestrator(
            use_mock=False,  # Never use mock in production - HF Inference is the free fallback
            mode=effective_mode,
            oauth_token=oauth_token,
            hf_model=hf_model if hf_model else None,  # Convert empty string to None
            hf_provider=hf_provider if hf_provider else None,  # Convert empty string to None
            graph_mode=graph_mode if graph_mode else None,
            use_graph=use_graph,
        )

        # Configure TTS defaults if not provided
        tts_voice_default, tts_speed_default, _, _, _ = configure_audio_tts()
        tts_voice = tts_voice or tts_voice_default
        tts_speed = tts_speed if tts_speed is not None else tts_speed_default

        yield {
            "role": "assistant",
            "content": f"🧠 **Backend**: {backend_name}\n\n",
        }, None

        # Handle orchestrator events and generate audio output
        audio_output_data: tuple[int, np.ndarray] | None = None
        final_message = ""

        async for msg in handle_orchestrator_events(orchestrator, processed_text):
            # Track final message for TTS
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                content = msg.get("content", "")
                metadata = msg.get("metadata", {})
                # This is the main response (not an accordion) if no title in metadata
                if content and not metadata.get("title"):
                    final_message = content

            # Yield without audio for intermediate messages
            yield msg, None

        # Generate audio output for final response
        if final_message and settings.enable_audio_output:
            try:
                audio_service = get_audio_service()
                # Use UI-configured voice and speed, fallback to settings defaults
                audio_output_data = await audio_service.generate_audio_output(
                    final_message,
                    voice=tts_voice or settings.tts_voice,
                    speed=tts_speed if tts_speed else settings.tts_speed,
                )
            except Exception as e:
                logger.warning("audio_synthesis_failed", error=str(e))
                # Continue without audio output

        # If we have audio output, we need to yield it with the final message
        # Note: The final message was already yielded above, so we yield None, audio_output_data
        # This will update the audio output component
        if audio_output_data is not None:
            yield None, audio_output_data

    except Exception as e:
        # Return error message without metadata to avoid issues during example caching
        # Metadata can cause validation errors when Gradio caches examples
        # Gradio Chatbot requires plain text - remove all markdown and special characters
        error_msg = str(e).replace("**", "").replace("*", "").replace("`", "")
        # Ensure content is a simple string without any special formatting
        yield {
            "role": "assistant",
            "content": f"Error: {error_msg}. Please check your configuration and try again.",
        }, None


def create_demo() -> gr.Blocks:
    """
    Create the Gradio demo interface with MCP support and OAuth login.

    Returns:
        Configured Gradio Blocks interface with MCP server and OAuth enabled
    """
    # DeepCritical-inspired theme stylesheet for the full interface. Adjust variables below to
    # tweak brand colors without changing functional behavior.
    brand_css = """
    :root {
        --brand-orange: #f28c28;
        --brand-red: #c53d2b;
        --brand-sand: #f7f3ed;
        --brand-ink: #1f2329;
    }

    .gradio-container {
        background: var(--brand-sand);
        color: var(--brand-ink);
    }

    #hero-banner {
        border: 1px solid #eadfd3;
        background: linear-gradient(120deg, #ffffff, #fbf6ef 35%, #fff9f1 70%);
        border-radius: 16px;
        padding: 22px 24px;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.08);
    }

    #hero-nav {
        background: #fff;
        border: 1px solid #eadfd3;
        border-radius: 12px;
        padding: 12px 14px;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
    }

    #hero-nav h4 {
        color: var(--brand-orange);
        margin-bottom: 10px;
    }

    #hero-nav li {
        margin-bottom: 4px;
        color: #3a3f45;
    }

    #hero-text h1, #hero-text h2, #hero-text h3, #hero-text h4 {
        color: #0f1216;
        margin-bottom: 8px;
    }

    #hero-text p {
        color: #383f47;
        font-size: 16px;
    }

    #hero-login {
        background: #fff;
        border: 1px solid #eadfd3;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.08);
    }

    #hero-login h4 {
        color: #0f1216;
        margin-bottom: 10px;
    }

    #hf-login button {
        width: 100%;
        background: linear-gradient(135deg, var(--brand-orange), var(--brand-red));
        color: white;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 10px 20px rgba(197, 61, 43, 0.25);
        transition: transform 160ms ease, box-shadow 160ms ease;
    }

    #hf-login button:hover {
        transform: translateY(-1px);
        box-shadow: 0 12px 26px rgba(242, 140, 40, 0.35);
    }

    #hf-login .sso-status {
        color: #3a3f45;
    }

    #login-note {
        color: #4d565f;
        font-size: 14px;
    }

    #chat-panel .wrap {
        background: #fff;
        border: 1px solid #eadfd3;
        border-radius: 14px;
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.08);
    }

    #chat-panel .message {
        background: #fff8f1;
        border: 1px solid rgba(242, 140, 40, 0.15);
    }

    #chat-panel .accordion {
        background: #fff;
    }

    #chat-panel .prose :where(h1, h2, h3, h4, h5, h6) {
        color: #0f1216;
    }

    #chat-panel .prose :where(p, li) {
        color: #3a3f45;
    }

    #settings-panel .gr-accordion .label-wrap {
        font-weight: 600;
    }
    """

    with gr.Blocks(title="🔬 The DETERMINATOR", fill_height=True) as demo:
        gr.HTML(f"<style>{brand_css}</style>")

        is_space = bool(os.getenv("SPACE_ID"))

        with gr.Row(elem_id="hero-banner"):
            with gr.Column(scale=2, elem_id="hero-nav"):
                gr.Markdown(
                    """#### Available Tools:

- Web Search: General knowledge
- search_pubmed: Peer-reviewed biomedical literature
- search_clinical_trials: ClinicalTrials.gov
- search_europepmc: bioRxiv/medRxiv preprints
- RAG: Semantic retrieval from ingested documents
""",
                )
            with gr.Column(scale=3, elem_id="hero-text"):
                gr.Markdown(
                    """## 🧬 The DETERMINATOR Research Agent
**Evidence-focused multimodal research with MCP integration.**

Multi-Source Search: Web, PubMed, ClinicalTrials.gov, Europe PMC, RAG
MCP Integration: Connect Claude Desktop to `/gradio_api/mcp/`
Modal Sandbox: Secure TTS and multimodal processing
LlamaIndex RAG: Semantic search and evidence synthesis
""",
                )
            with gr.Column(scale=2, elem_id="hero-login"):
                gr.Markdown("#### Sign in to unlock premium reasoning models")
                if is_space:
                    gr.LoginButton(
                        elem_id="hf-login",
                        value="Sign in with Hugging Face",
                    )
                    login_note = (
                        "Connect your Hugging Face account to access faster providers, gated models, and richer summaries."
                    )
                else:
                    gr.Button(
                        value="Sign in with Hugging Face",
                        elem_id="hf-login",
                        interactive=False,
                    )
                    login_note = (
                        "Sign-in is available on the deployed Hugging Face Space. Local previews use public model access."
                    )
                gr.Markdown(login_note, elem_id="login-note")

        with gr.Row(elem_id="content-row"):
            with gr.Column(scale=2, elem_id="settings-panel"):
                gr.Markdown("### ⚙️ Research Settings")

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

                    gr.Markdown("### 🤖 Model & Provider")

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
                        info="Select a HuggingFace model (leave empty for default)",
                        allow_custom_value=True,
                    )

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
                        info="Select inference provider (leave empty for auto-select)",
                    )

                with gr.Accordion("📷 Multimodal Input", open=False):
                    enable_image_input_checkbox = gr.Checkbox(
                        value=settings.enable_image_input,
                        label="Enable Image Input (OCR)",
                        info="Extract text from uploaded images using OCR",
                    )

                    enable_audio_input_checkbox = gr.Checkbox(
                        value=settings.enable_audio_input,
                        label="Enable Audio Input (STT)",
                        info="Transcribe audio recordings using speech-to-text",
                    )

                with gr.Accordion("🔊 Audio Output", open=False):
                    tts_voice_default = getattr(settings, "tts_voice", "af_heart")
                    tts_speed_default = getattr(settings, "tts_speed", 1.0)
                    tts_gpu_default = getattr(settings, "tts_gpu", "T4")
                    tts_region_default = getattr(settings, "tts_region", "us-east-1")
                    tts_env_default = getattr(settings, "tts_environment", "prod")

                    enable_audio_output_checkbox = gr.Checkbox(
                        value=settings.enable_audio_output,
                        label="Enable Audio Output",
                        info="Generate audio responses using TTS",
                    )

                    tts_voice_dropdown = gr.Dropdown(
                        choices=[
                            "af_heart",
                            "af_bella",
                            "af_nicole",
                            "af_aoede",
                            "af_kore",
                            "af_sarah",
                            "af_nova",
                            "af_sky",
                            "af_alloy",
                            "af_jessica",
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
                        value=tts_voice_default,
                        label="TTS Voice",
                        info="Select TTS voice (American English voices: af_*, am_*)",
                    )

                    tts_speed_slider = gr.Slider(
                        minimum=0.5,
                        maximum=2.0,
                        value=tts_speed_default,
                        step=0.1,
                        label="TTS Speech Speed",
                        info="Adjust TTS speech speed (0.5x to 2.0x)",
                    )

                    tts_gpu_dropdown = gr.Dropdown(
                        choices=["T4", "A10", "A100", "L4", "L40S"],
                        value=tts_gpu_default,
                        label="TTS GPU Type",
                        info="Modal GPU type for TTS (T4 is cheapest, A100 is fastest). Note: GPU changes require app restart.",
                    )

                    tts_region_dropdown = gr.Dropdown(
                        choices=["us-east-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-southeast-1"],
                        value=tts_region_default,
                        label="TTS Region",
                        info="Modal region for TTS deployment",
                    )

                    tts_env_dropdown = gr.Dropdown(
                        choices=["prod", "staging", "dev"],
                        value=tts_env_default,
                        label="TTS Environment",
                        info="Modal environment for TTS deployment",
                    )

                gr.Markdown(
                    "**Need help?**\n"
                    "- Ensure you're logged in with Hugging Face.\n"
                    "- Select a model and provider.\n"
                    "- Configure multimodal inputs if needed.\n"
                    "- Audio output requires Modal credentials (see README).",
                )

            with gr.Column(scale=3, elem_id="chat-panel"):
                audio_output = gr.Audio(
                    type="numpy",
                    label="🔊 Audio Response",
                    visible=getattr(settings, "enable_audio_output", False),
                )

                def update_tts_visibility(enabled: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
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

                gr.ChatInterface(
                    fn=research_agent,
                    multimodal=True,
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
                        [
                            "Create a comprehensive report on Long COVID treatments including clinical trials, mechanisms, and safety.",
                            "deep",
                            "zai-org/GLM-4.5-Air",
                            "nebius",
                            "deep",
                            True,
                        ],
                        [
                            "Analyze the current state of quantum computing architectures: compare different qubit technologies, error correction methods, and scalability challenges across major platforms including IBM, Google, and IonQ.",
                            "deep",
                            "Qwen/Qwen3-Next-80B-A3B-Thinking",
                            "",
                            "deep",
                            True,
                        ],
                        [
                            "Investigate the economic and environmental impact of renewable energy transition: analyze cost trends, grid integration challenges, policy frameworks, and market dynamics across solar, wind, and battery storage technologies, in china",
                            "deep",
                            "Qwen/Qwen3-235B-A22B-Instruct-2507",
                            "",
                            "deep",
                            True,
                        ],
                    ],
                    cache_examples=False,
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
                    ],
                    additional_outputs=[audio_output],
                )

    return demo  # type: ignore[no-any-return]


def main() -> None:
    """Run the Gradio app with MCP server enabled."""
    demo = create_demo()
    demo.launch(
        # server_name="0.0.0.0",
        # server_port=7860,
        # share=False,
        mcp_server=True,  # Enable MCP server for Claude Desktop integration
        ssr_mode=False,  # Fix for intermittent loading/hydration issues in HF Spaces
    )


if __name__ == "__main__":
    main()
