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
from src.utils.message_history import convert_gradio_to_message_history
from src.utils.models import AgentEvent, OrchestratorConfig

try:
    from pydantic_ai import ModelMessage
except ImportError:
    ModelMessage = Any  # type: ignore[assignment, misc]

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
        auth_source = "OAuth token" if oauth_token else ("HF_TOKEN env var" if os.getenv("HF_TOKEN") else "HUGGINGFACE_API_KEY env var")
        logger.info("Using HuggingFace authentication", source=auth_source, has_token=bool(effective_api_key))

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
        file_path: Full file path
        
    Returns:
        Filename with extension
    """
    import os
    return os.path.basename(file_path)


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
        # Check if event contains file information
        content = event.message
        files: list[str] | None = None
        
        # Check event.data for file paths
        if event.data and isinstance(event.data, dict):
            # Support both "files" (list) and "file" (single path) keys
            if "files" in event.data:
                files = event.data["files"]
                if isinstance(files, str):
                    files = [files]
                elif not isinstance(files, list):
                    files = None
                else:
                    # Filter to only valid file paths
                    files = [f for f in files if isinstance(f, str) and _is_file_path(f)]
            elif "file" in event.data:
                file_path = event.data["file"]
                if isinstance(file_path, str) and _is_file_path(file_path):
                    files = [file_path]
        
        # Also check if message itself is a file path (less common, but possible)
        if not files and isinstance(event.message, str) and _is_file_path(event.message):
            files = [event.message]
            # Keep message as text description
            content = "Report generated. Download available below."
        
        # Return as dict format for Gradio Chatbot compatibility
        result: dict[str, Any] = {
            "role": "assistant",
            "content": content,
        }
        
        # Add files if present
        # Gradio Chatbot supports file paths in content as markdown links
        # The links will be clickable and downloadable
        if files:
            # Validate files exist before including them
            import os
            valid_files = [f for f in files if os.path.exists(f)]
            
            if valid_files:
                # Format files for Gradio: include as markdown download links
                # Gradio ChatInterface automatically renders file links as downloadable files
                import os
                file_links = []
                for f in valid_files:
                    file_name = _get_file_name(f)
                    try:
                        file_size = os.path.getsize(f)
                        # Format file size (bytes to KB/MB)
                        if file_size < 1024:
                            size_str = f"{file_size} B"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size / 1024:.1f} KB"
                        else:
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"
                        file_links.append(f"📎 [Download: {file_name} ({size_str})]({f})")
                    except OSError:
                        # If we can't get file size, just show the name
                        file_links.append(f"📎 [Download: {file_name}]({f})")
                
                result["content"] = f"{content}\n\n" + "\n\n".join(file_links)
                
                # Also store in metadata for potential future use
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["files"] = valid_files
        
        return result

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

    # Advanced mode is not currently supported with HuggingFace inference
    # For now, we only support simple mode with HuggingFace
    if mode == "advanced":
        yield {
            "role": "assistant",
            "content": (
                "⚠️ **Note**: Advanced mode is not available with HuggingFace inference providers. "
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
    conversation_history: list[ModelMessage] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Handle orchestrator events and yield ChatMessages.

    Args:
        orchestrator: The orchestrator instance
        message: The research question
        conversation_history: Optional user conversation history

    Yields:
        ChatMessage objects from orchestrator events
    """
    # Track pending accordions for real-time updates
    pending_accordions: dict[str, str] = {}  # title -> accumulated content

    async for event in orchestrator.run(message, message_history=conversation_history):
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
    oauth_token: gr.OAuthToken | None = None,
    oauth_profile: gr.OAuthProfile | None = None,
) -> AsyncGenerator[dict[str, Any] | tuple[dict[str, Any], tuple[int, np.ndarray] | None], None]:
    """
    Gradio chat function that runs the research agent.

    Args:
        message: User's research question (str or MultimodalPostprocess with text/files)
        history: Chat history (Gradio format)
        mode: Orchestrator mode ("simple" or "advanced")
        hf_model: Selected HuggingFace model ID (from dropdown)
        hf_provider: Selected inference provider (from dropdown)
        oauth_token: Gradio OAuth token (None if user not logged in)
        oauth_profile: Gradio OAuth profile (None if user not logged in)

    Yields:
        ChatMessage objects with metadata for accordion display, optionally with audio output
    """
    import structlog

    logger = structlog.get_logger()

    # REQUIRE LOGIN BEFORE USE
    # Extract OAuth token and username using Gradio's OAuth types
    # According to Gradio docs: OAuthToken and OAuthProfile are None if user not logged in
    token_value: str | None = None
    username: str | None = None

    if oauth_token is not None:
        # OAuthToken has a .token attribute containing the access token
        if hasattr(oauth_token, "token"):
            token_value = oauth_token.token
            logger.debug("OAuth token extracted from oauth_token.token attribute")
        elif isinstance(oauth_token, str):
            # Handle case where oauth_token is already a string (shouldn't happen but defensive)
            token_value = oauth_token
            logger.debug("OAuth token extracted as string")
        else:
            token_value = None
            logger.warning("OAuth token object present but token extraction failed", oauth_token_type=type(oauth_token).__name__)

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
        if username:
            logger.info("OAuth user authenticated", username=username)

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
        }, None
        return

    # Process multimodal input (text + images + audio)
    processed_text = ""
    audio_input_data: tuple[int, np.ndarray] | None = None

    if isinstance(message, dict):
        # MultimodalPostprocess format: {"text": str, "files": list[FileData], "audio": tuple | None}
        processed_text = message.get("text", "") or ""
        files = message.get("files", [])
        # Check for audio input in message (Gradio may include it as a separate field)
        audio_input_data = message.get("audio") or None

        # Process multimodal input (images, audio files, audio input)
        # Process if we have files (and image input enabled) or audio input (and audio input enabled)
        # Use UI settings from function parameters
        if (files and enable_image_input) or (audio_input_data is not None and enable_audio_input):
            try:
                multimodal_service = get_multimodal_service()
                # Prepend audio/image text to original text (prepend_multimodal=True)
                # Filter files and audio based on UI settings
                processed_text = await multimodal_service.process_multimodal_input(
                    processed_text,
                    files=files if enable_image_input else [],
                    audio_input=audio_input_data if enable_audio_input else None,
                    hf_token=token_value,
                    prepend_multimodal=True,  # Prepend audio/image text to text input
                )
            except Exception as e:
                logger.warning("multimodal_processing_failed", error=str(e))
                # Continue with text-only input
    else:
        # Plain string message
        processed_text = str(message) if message else ""

    if not processed_text.strip():
        yield {
            "role": "assistant",
            "content": "Please enter a research question or provide an image/audio input.",
        }, None
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
        auth_source = "OAuth" if token_value else ("Env (HF_TOKEN)" if os.getenv("HF_TOKEN") else ("Env (HUGGINGFACE_API_KEY)" if os.getenv("HUGGINGFACE_API_KEY") else "None"))
        logger.info(
            "Configuring orchestrator",
            mode=effective_mode,
            auth_source=auth_source,
            has_oauth_token=bool(token_value),
            model=model_id or "default",
            provider=provider_name or "auto",
        )

        orchestrator, backend_name = configure_orchestrator(
            use_mock=False,  # Never use mock in production - HF Inference is the free fallback
            mode=effective_mode,
            oauth_token=token_value,  # Use extracted token value - passed to all agents and services
            hf_model=model_id,  # None will use defaults in configure_orchestrator
            hf_provider=provider_name,  # None will use defaults in configure_orchestrator
            graph_mode=graph_mode if graph_mode else None,
            use_graph=use_graph,
        )

        yield {
            "role": "assistant",
            "content": f"🧠 **Backend**: {backend_name}\n\n",
        }

        # Convert Gradio history to message history
        message_history = convert_gradio_to_message_history(history) if history else None
        if message_history:
            logger.info(
                "Using conversation history",
                turns=len(message_history) // 2,  # Approximate turn count
            )

        # Handle orchestrator events and generate audio output
        audio_output_data: tuple[int, np.ndarray] | None = None
        final_message = ""

        async for msg in handle_orchestrator_events(
            orchestrator, processed_text, conversation_history=message_history
        ):
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
                
                # Popular models list
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
                    allow_custom_value=True,  # Allow users to type custom model IDs
                )

                # Provider list from README
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
            
            # Multimodal Input Configuration Accordion
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
            
            # Audio/TTS Configuration Accordion
            with gr.Accordion("🔊 Audio Output", open=False):
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
                
                tts_gpu_dropdown = gr.Dropdown(
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
                    "",
                    "deep",
                    True,
                ],
                [
                    # Business/Scientific example requiring iterative search
                    "Investigate the economic and environmental impact of renewable energy transition: analyze cost trends, grid integration challenges, policy frameworks, and market dynamics across solar, wind, and battery storage technologies, in china",
                    "deep",
                    "Qwen/Qwen3-235B-A22B-Instruct-2507",
                    "",
                    "deep",
                    True,
                ],
            ],
            cache_examples=False,  # CRITICAL: Disable example caching to prevent examples from running at startup
            # Examples will only run when user explicitly clicks them (after login)
            # Note: additional_inputs_accordion is not a valid parameter in Gradio 6.0 ChatInterface
            # Components will be displayed in the order provided
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
                # Note: gr.OAuthToken and gr.OAuthProfile are automatically passed as function parameters
                # when user is logged in - they should NOT be added to additional_inputs
            ],
            additional_outputs=[audio_output],  # Add audio output for TTS
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
