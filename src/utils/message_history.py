"""Message history utilities for Pydantic AI integration."""

from typing import Any

import structlog

try:
    from pydantic_ai import ModelMessage, ModelRequest, ModelResponse
    from pydantic_ai.messages import TextPart, UserPromptPart

    _PYDANTIC_AI_AVAILABLE = True
except ImportError:
    # Fallback for older pydantic-ai versions
    ModelMessage = Any  # type: ignore[assignment, misc]
    ModelRequest = Any  # type: ignore[assignment, misc]
    ModelResponse = Any  # type: ignore[assignment, misc]
    TextPart = Any  # type: ignore[assignment, misc]
    UserPromptPart = Any  # type: ignore[assignment, misc]
    _PYDANTIC_AI_AVAILABLE = False

logger = structlog.get_logger()


def convert_gradio_to_message_history(
    history: list[dict[str, Any]],
    max_messages: int = 20,
) -> list[ModelMessage]:
    """
    Convert Gradio chat history to Pydantic AI message history.

    Args:
        history: Gradio chat history format [{"role": "user", "content": "..."}, ...]
        max_messages: Maximum messages to include (most recent)

    Returns:
        List of ModelMessage objects for Pydantic AI
    """
    if not history:
        return []

    if not _PYDANTIC_AI_AVAILABLE:
        logger.warning(
            "Pydantic AI message history not available, returning empty list",
        )
        return []

    messages: list[ModelMessage] = []

    # Take most recent messages
    recent = history[-max_messages:] if len(history) > max_messages else history

    for msg in recent:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if not content or role not in ("user", "assistant"):
            continue

        # Convert content to string if needed
        content_str = str(content)

        if role == "user":
            messages.append(
                ModelRequest(parts=[UserPromptPart(content=content_str)]),
            )
        elif role == "assistant":
            messages.append(
                ModelResponse(parts=[TextPart(content=content_str)]),
            )

    logger.debug(
        "Converted Gradio history to message history",
        input_turns=len(history),
        output_messages=len(messages),
    )

    return messages


def message_history_to_string(
    messages: list[ModelMessage],
    max_messages: int = 5,
    include_metadata: bool = False,
) -> str:
    """
    Convert message history to string format for backward compatibility.

    Used during transition period when some agents still expect strings.

    Args:
        messages: List of ModelMessage objects
        max_messages: Maximum messages to include
        include_metadata: Whether to include metadata

    Returns:
        Formatted string representation
    """
    if not messages:
        return ""

    recent = messages[-max_messages:] if len(messages) > max_messages else messages

    parts = ["PREVIOUS CONVERSATION:", "---"]
    turn_num = 1

    for msg in recent:
        # Extract text content
        text = ""
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if hasattr(part, "content"):
                    text += str(part.content)
            parts.append(f"[Turn {turn_num}]")
            parts.append(f"User: {text}")
            turn_num += 1
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if hasattr(part, "content"):
                    text += str(part.content)
            parts.append(f"Assistant: {text}")

    parts.append("---")
    return "\n".join(parts)


def create_truncation_processor(max_messages: int = 10):
    """Create a history processor that keeps only the most recent N messages.

    Args:
        max_messages: Maximum number of messages to keep

    Returns:
        Processor function that takes a list of messages and returns truncated list
    """

    def processor(messages: list[ModelMessage]) -> list[ModelMessage]:
        return messages[-max_messages:] if len(messages) > max_messages else messages

    return processor


def create_relevance_processor(min_length: int = 10):
    """Create a history processor that filters out very short messages.

    Args:
        min_length: Minimum message length to keep

    Returns:
        Processor function that filters messages by length
    """

    def processor(messages: list[ModelMessage]) -> list[ModelMessage]:
        filtered = []
        for msg in messages:
            text = ""
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if hasattr(part, "content"):
                        text += str(part.content)
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if hasattr(part, "content"):
                        text += str(part.content)

            if len(text.strip()) >= min_length:
                filtered.append(msg)
        return filtered

    return processor



