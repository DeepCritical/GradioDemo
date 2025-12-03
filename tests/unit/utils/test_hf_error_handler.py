"""Unit tests for HuggingFace error handling utilities."""

from unittest.mock import patch

import pytest

from src.utils.hf_error_handler import (
    extract_error_details,
    get_fallback_models,
    get_user_friendly_error_message,
    log_token_info,
    should_retry_with_fallback,
    validate_hf_token,
)


class TestExtractErrorDetails:
    """Tests for extract_error_details function."""

    def test_extract_403_error(self) -> None:
        """Should extract 403 error details correctly."""
        error = Exception("status_code: 403, model_name: Qwen/Qwen3-Next-80B-A3B-Thinking, body: Forbidden")
        details = extract_error_details(error)
        
        assert details["status_code"] == 403
        assert details["model_name"] == "Qwen/Qwen3-Next-80B-A3B-Thinking"
        assert details["body"] == "Forbidden"
        assert details["error_type"] == "http_403"
        assert details["is_auth_error"] is True
        assert details["is_model_error"] is False

    def test_extract_422_error(self) -> None:
        """Should extract 422 error details correctly."""
        error = Exception("status_code: 422, model_name: meta-llama/Llama-3.1-70B-Instruct, body: Unprocessable Entity")
        details = extract_error_details(error)
        
        assert details["status_code"] == 422
        assert details["model_name"] == "meta-llama/Llama-3.1-70B-Instruct"
        assert details["body"] == "Unprocessable Entity"
        assert details["error_type"] == "http_422"
        assert details["is_auth_error"] is False
        assert details["is_model_error"] is True

    def test_extract_partial_error(self) -> None:
        """Should handle partial error information."""
        error = Exception("status_code: 500")
        details = extract_error_details(error)
        
        assert details["status_code"] == 500
        assert details["model_name"] is None
        assert details["body"] is None
        assert details["error_type"] == "http_500"
        assert details["is_auth_error"] is False
        assert details["is_model_error"] is False

    def test_extract_generic_error(self) -> None:
        """Should handle generic errors without status codes."""
        error = Exception("Something went wrong")
        details = extract_error_details(error)
        
        assert details["status_code"] is None
        assert details["model_name"] is None
        assert details["body"] is None
        assert details["error_type"] == "unknown"
        assert details["is_auth_error"] is False
        assert details["is_model_error"] is False


class TestGetUserFriendlyErrorMessage:
    """Tests for get_user_friendly_error_message function."""

    def test_403_error_message(self) -> None:
        """Should generate user-friendly 403 error message."""
        error = Exception("status_code: 403, model_name: Qwen/Qwen3-Next-80B-A3B-Thinking, body: Forbidden")
        message = get_user_friendly_error_message(error)
        
        assert "Authentication Error" in message
        assert "inference-api" in message
        assert "Qwen/Qwen3-Next-80B-A3B-Thinking" in message
        assert "Forbidden" in message

    def test_422_error_message(self) -> None:
        """Should generate user-friendly 422 error message."""
        error = Exception("status_code: 422, model_name: meta-llama/Llama-3.1-70B-Instruct, body: Unprocessable Entity")
        message = get_user_friendly_error_message(error)
        
        assert "Model Compatibility Error" in message
        assert "meta-llama/Llama-3.1-70B-Instruct" in message
        assert "Unprocessable Entity" in message

    def test_generic_error_message(self) -> None:
        """Should generate generic error message for unknown errors."""
        error = Exception("Something went wrong")
        message = get_user_friendly_error_message(error)
        
        assert "API Error" in message
        assert "Something went wrong" in message

    def test_error_message_with_model_name_param(self) -> None:
        """Should use provided model_name parameter when not in error."""
        error = Exception("status_code: 403, body: Forbidden")
        message = get_user_friendly_error_message(error, model_name="test-model")
        
        assert "test-model" in message


class TestValidateHfToken:
    """Tests for validate_hf_token function."""

    def test_valid_token(self) -> None:
        """Should validate a valid token."""
        token = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        is_valid, error_msg = validate_hf_token(token)
        
        assert is_valid is True
        assert error_msg is None

    def test_none_token(self) -> None:
        """Should reject None token."""
        is_valid, error_msg = validate_hf_token(None)
        
        assert is_valid is False
        assert "None or empty" in error_msg

    def test_empty_token(self) -> None:
        """Should reject empty token."""
        is_valid, error_msg = validate_hf_token("")
        
        assert is_valid is False
        assert "None or empty" in error_msg

    def test_non_string_token(self) -> None:
        """Should reject non-string token."""
        is_valid, error_msg = validate_hf_token(123)  # type: ignore[arg-type]
        
        assert is_valid is False
        assert "not a string" in error_msg

    def test_short_token(self) -> None:
        """Should reject token that's too short."""
        is_valid, error_msg = validate_hf_token("hf_123")
        
        assert is_valid is False
        assert "too short" in error_msg

    def test_oauth_token_format(self) -> None:
        """Should accept OAuth tokens (may not start with hf_)."""
        # OAuth tokens may have different formats
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
        is_valid, error_msg = validate_hf_token(token)
        
        assert is_valid is True
        assert error_msg is None


class TestLogTokenInfo:
    """Tests for log_token_info function."""

    @patch("src.utils.hf_error_handler.logger")
    def test_log_valid_token(self, mock_logger) -> None:
        """Should log token info for valid token."""
        token = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        log_token_info(token, context="test")
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "Token validation"
        assert call_args[1]["context"] == "test"
        assert call_args[1]["has_token"] is True
        assert call_args[1]["is_valid"] is True
        assert call_args[1]["token_length"] == len(token)
        assert "token_prefix" in call_args[1]

    @patch("src.utils.hf_error_handler.logger")
    def test_log_none_token(self, mock_logger) -> None:
        """Should log None token info."""
        log_token_info(None, context="test")
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "Token validation"
        assert call_args[1]["context"] == "test"
        assert call_args[1]["has_token"] is False


class TestShouldRetryWithFallback:
    """Tests for should_retry_with_fallback function."""

    def test_403_error_should_retry(self) -> None:
        """Should retry for 403 errors."""
        error = Exception("status_code: 403, model_name: test-model, body: Forbidden")
        assert should_retry_with_fallback(error) is True

    def test_422_error_should_retry(self) -> None:
        """Should retry for 422 errors."""
        error = Exception("status_code: 422, model_name: test-model, body: Unprocessable Entity")
        assert should_retry_with_fallback(error) is True

    def test_model_specific_error_should_retry(self) -> None:
        """Should retry for model-specific errors."""
        error = Exception("status_code: 500, model_name: test-model, body: Error")
        assert should_retry_with_fallback(error) is True

    def test_generic_error_should_not_retry(self) -> None:
        """Should not retry for generic errors without model info."""
        error = Exception("Something went wrong")
        assert should_retry_with_fallback(error) is False


class TestGetFallbackModels:
    """Tests for get_fallback_models function."""

    def test_get_fallback_models_default(self) -> None:
        """Should return default fallback models."""
        fallbacks = get_fallback_models()
        
        assert len(fallbacks) > 0
        assert "meta-llama/Llama-3.1-8B-Instruct" in fallbacks
        assert isinstance(fallbacks, list)

    def test_get_fallback_models_excludes_original(self) -> None:
        """Should exclude original model from fallbacks."""
        original = "meta-llama/Llama-3.1-8B-Instruct"
        fallbacks = get_fallback_models(original_model=original)
        
        assert original not in fallbacks
        assert len(fallbacks) > 0

    def test_get_fallback_models_with_unknown_original(self) -> None:
        """Should return all fallbacks if original is not in list."""
        original = "unknown/model"
        fallbacks = get_fallback_models(original_model=original)
        
        # Should still have all fallbacks since original is not in the list
        assert len(fallbacks) >= 3  # At least 3 fallback models

