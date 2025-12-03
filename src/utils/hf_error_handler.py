"""Utility functions for handling HuggingFace API errors and token validation."""

import re
from typing import Any

import structlog

logger = structlog.get_logger()


def extract_error_details(error: Exception) -> dict[str, Any]:
    """Extract error details from HuggingFace API errors.

    Pydantic AI and HuggingFace Inference API errors often contain
    information in the error message string like:
    "status_code: 403, model_name: Qwen/Qwen3-Next-80B-A3B-Thinking, body: Forbidden"

    Args:
        error: The exception object

    Returns:
        Dictionary with extracted error details:
        - status_code: HTTP status code (if found)
        - model_name: Model name (if found)
        - body: Error body/message (if found)
        - error_type: Type of error (403, 422, etc.)
        - is_auth_error: Whether this is an authentication/authorization error
        - is_model_error: Whether this is a model-specific error
    """
    error_str = str(error)
    details: dict[str, Any] = {
        "status_code": None,
        "model_name": None,
        "body": None,
        "error_type": "unknown",
        "is_auth_error": False,
        "is_model_error": False,
    }

    # Try to extract status_code
    status_match = re.search(r"status_code:\s*(\d+)", error_str)
    if status_match:
        details["status_code"] = int(status_match.group(1))
        details["error_type"] = f"http_{details['status_code']}"

        # Determine error category
        if details["status_code"] == 403:
            details["is_auth_error"] = True
        elif details["status_code"] == 422:
            details["is_model_error"] = True

    # Try to extract model_name
    model_match = re.search(r"model_name:\s*([^\s,]+)", error_str)
    if model_match:
        details["model_name"] = model_match.group(1)

    # Try to extract body
    body_match = re.search(r"body:\s*(.+)", error_str)
    if body_match:
        details["body"] = body_match.group(1).strip()

    return details


def get_user_friendly_error_message(error: Exception, model_name: str | None = None) -> str:
    """Generate a user-friendly error message from an exception.

    Args:
        error: The exception object
        model_name: Optional model name for context

    Returns:
        User-friendly error message
    """
    details = extract_error_details(error)

    if details["is_auth_error"]:
        return (
            "🔐 **Authentication Error**\n\n"
            "Your HuggingFace token doesn't have permission to access this model or API.\n\n"
            "**Possible solutions:**\n"
            "1. **Re-authenticate**: Log out and log back in to ensure your token has the `inference-api` scope\n"
            "2. **Check model access**: Visit the model page on HuggingFace and request access if it's gated\n"
            "3. **Use alternative model**: Try a different model that's publicly available\n\n"
            f"**Model attempted**: {details['model_name'] or model_name or 'Unknown'}\n"
            f"**Error**: {details['body'] or str(error)}"
        )

    if details["is_model_error"]:
        return (
            "⚠️ **Model Compatibility Error**\n\n"
            "The selected model is not compatible with the current provider or has specific requirements.\n\n"
            "**Possible solutions:**\n"
            "1. **Try a different model**: Use a model that's compatible with the current provider\n"
            "2. **Check provider status**: The provider may be in staging mode or unavailable\n"
            "3. **Wait and retry**: If the model is in staging, it may become available later\n\n"
            f"**Model attempted**: {details['model_name'] or model_name or 'Unknown'}\n"
            f"**Error**: {details['body'] or str(error)}"
        )

    # Generic error
    return (
        "❌ **API Error**\n\n"
        f"An error occurred while calling the HuggingFace API:\n\n"
        f"**Error**: {error!s}\n\n"
        "Please try again or contact support if the issue persists."
    )


def validate_hf_token(token: str | None) -> tuple[bool, str | None]:
    """Validate HuggingFace token format.

    Args:
        token: The token to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if token appears valid
        - error_message: Error message if invalid, None if valid
    """
    if not token:
        return False, "Token is None or empty"

    if not isinstance(token, str):
        return False, f"Token is not a string (type: {type(token).__name__})"

    if len(token) < 10:
        return False, "Token appears too short (minimum 10 characters expected)"

    # HuggingFace tokens typically start with "hf_" for user tokens
    # OAuth tokens may have different formats, so we're lenient
    # Just check it's not obviously invalid

    return True, None


def log_token_info(token: str | None, context: str = "") -> None:
    """Log token information for debugging (without exposing the actual token).

    Args:
        token: The token to log info about
        context: Additional context for the log message
    """
    if token:
        is_valid, error_msg = validate_hf_token(token)
        logger.debug(
            "Token validation",
            context=context,
            has_token=True,
            is_valid=is_valid,
            token_length=len(token),
            token_prefix=token[:4] + "..." if len(token) > 4 else "***",
            validation_error=error_msg,
        )
    else:
        logger.debug("Token validation", context=context, has_token=False)


def should_retry_with_fallback(error: Exception) -> bool:
    """Determine if an error should trigger a fallback to alternative models.

    Args:
        error: The exception object

    Returns:
        True if the error suggests we should try a fallback model
    """
    details = extract_error_details(error)

    # Retry with fallback for:
    # - 403 errors (authentication/permission issues - might work with different model)
    # - 422 errors (model/provider compatibility - definitely try different model)
    # - Model-specific errors
    return (
        details["is_auth_error"] or details["is_model_error"] or details["model_name"] is not None
    )


def get_fallback_models(original_model: str | None = None) -> list[str]:
    """Get a list of fallback models to try.

    Args:
        original_model: The original model that failed

    Returns:
        List of fallback model names to try in order
    """
    # Publicly available models that should work with most tokens
    fallbacks = [
        "meta-llama/Llama-3.1-8B-Instruct",  # Common, often available
        "mistralai/Mistral-7B-Instruct-v0.3",  # Alternative
        "HuggingFaceH4/zephyr-7b-beta",  # Ungated fallback
    ]

    # If original model is in the list, remove it
    if original_model and original_model in fallbacks:
        fallbacks.remove(original_model)

    return fallbacks
