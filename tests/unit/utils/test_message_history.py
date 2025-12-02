"""Unit tests for message history utilities."""

import pytest

pytestmark = pytest.mark.unit

from src.utils.message_history import (
    convert_gradio_to_message_history,
    create_relevance_processor,
    create_truncation_processor,
    message_history_to_string,
)


def test_convert_gradio_to_message_history_empty():
    """Test conversion with empty history."""
    result = convert_gradio_to_message_history([])
    assert result == []


def test_convert_gradio_to_message_history_single_turn():
    """Test conversion with a single turn."""
    gradio_history = [
        {"role": "user", "content": "What is AI?"},
        {"role": "assistant", "content": "AI is artificial intelligence."},
    ]
    result = convert_gradio_to_message_history(gradio_history)
    assert len(result) == 2


def test_convert_gradio_to_message_history_multiple_turns():
    """Test conversion with multiple turns."""
    gradio_history = [
        {"role": "user", "content": "What is AI?"},
        {"role": "assistant", "content": "AI is artificial intelligence."},
        {"role": "user", "content": "Tell me more"},
        {"role": "assistant", "content": "AI includes machine learning..."},
    ]
    result = convert_gradio_to_message_history(gradio_history)
    assert len(result) == 4


def test_convert_gradio_to_message_history_max_messages():
    """Test conversion with max_messages limit."""
    gradio_history = []
    for i in range(15):  # Create 15 turns
        gradio_history.append({"role": "user", "content": f"Message {i}"})
        gradio_history.append({"role": "assistant", "content": f"Response {i}"})

    result = convert_gradio_to_message_history(gradio_history, max_messages=10)
    # Should only include most recent 10 messages
    assert len(result) <= 10


def test_convert_gradio_to_message_history_filters_invalid():
    """Test that invalid entries are filtered out."""
    gradio_history = [
        {"role": "user", "content": "Valid message"},
        {"role": "system", "content": "Should be filtered"},
        {"role": "assistant", "content": ""},  # Empty content should be filtered
        {"role": "assistant", "content": "Valid response"},
    ]
    result = convert_gradio_to_message_history(gradio_history)
    # Should only have 2 valid messages (user + assistant)
    assert len(result) == 2


def test_message_history_to_string_empty():
    """Test string conversion with empty history."""
    result = message_history_to_string([])
    assert result == ""


def test_message_history_to_string_format():
    """Test string conversion format."""
    # Create mock message history
    try:
        from pydantic_ai import ModelRequest, ModelResponse
        from pydantic_ai.messages import TextPart, UserPromptPart

        messages = [
            ModelRequest(parts=[UserPromptPart(content="Question 1")]),
            ModelResponse(parts=[TextPart(content="Answer 1")]),
        ]
        result = message_history_to_string(messages)
        assert "PREVIOUS CONVERSATION" in result
        assert "User:" in result
        assert "Assistant:" in result
    except ImportError:
        # Skip if pydantic_ai not available
        pytest.skip("pydantic_ai not available")


def test_message_history_to_string_max_messages():
    """Test string conversion with max_messages limit."""
    try:
        from pydantic_ai import ModelRequest, ModelResponse
        from pydantic_ai.messages import TextPart, UserPromptPart

        messages = []
        for i in range(10):  # Create 10 turns
            messages.append(ModelRequest(parts=[UserPromptPart(content=f"Question {i}")]))
            messages.append(ModelResponse(parts=[TextPart(content=f"Answer {i}")]))

        result = message_history_to_string(messages, max_messages=3)
        # Should only include most recent 3 messages (1.5 turns)
        assert result != ""
    except ImportError:
        pytest.skip("pydantic_ai not available")


def test_create_truncation_processor():
    """Test truncation processor factory."""
    processor = create_truncation_processor(max_messages=5)
    assert callable(processor)

    try:
        from pydantic_ai import ModelRequest
        from pydantic_ai.messages import UserPromptPart

        messages = [
            ModelRequest(parts=[UserPromptPart(content=f"Message {i}")])
            for i in range(10)
        ]
        result = processor(messages)
        assert len(result) == 5
    except ImportError:
        pytest.skip("pydantic_ai not available")


def test_create_relevance_processor():
    """Test relevance processor factory."""
    processor = create_relevance_processor(min_length=10)
    assert callable(processor)

    try:
        from pydantic_ai import ModelRequest, ModelResponse
        from pydantic_ai.messages import TextPart, UserPromptPart

        messages = [
            ModelRequest(parts=[UserPromptPart(content="Short")]),  # Too short
            ModelRequest(parts=[UserPromptPart(content="This is a longer message")]),  # Valid
            ModelResponse(parts=[TextPart(content="OK")]),  # Too short
            ModelResponse(parts=[TextPart(content="This is a valid response")]),  # Valid
        ]
        result = processor(messages)
        # Should only keep messages with length >= 10
        assert len(result) == 2
    except ImportError:
        pytest.skip("pydantic_ai not available")

