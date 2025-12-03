"""Unit tests for OAuth-related functions in app.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock gradio and its dependencies before importing app functions
import sys
from unittest.mock import MagicMock as Mock

# Create a comprehensive gradio mock
mock_gradio = Mock()
mock_gradio.OAuthToken = Mock
mock_gradio.OAuthProfile = Mock
mock_gradio.Request = Mock
mock_gradio.update = Mock(return_value={"choices": [], "value": ""})
mock_gradio.Blocks = Mock
mock_gradio.Markdown = Mock
mock_gradio.LoginButton = Mock
mock_gradio.Dropdown = Mock
mock_gradio.Textbox = Mock
mock_gradio.State = Mock

# Mock gradio.data_classes
mock_gradio.data_classes = Mock()
mock_gradio.data_classes.FileData = Mock()

sys.modules["gradio"] = mock_gradio
sys.modules["gradio.data_classes"] = mock_gradio.data_classes

# Mock other dependencies that might be imported
sys.modules["neo4j"] = Mock()
sys.modules["neo4j"].GraphDatabase = Mock()

from src.app import extract_oauth_info, update_model_provider_dropdowns


class TestExtractOAuthInfo:
    """Tests for extract_oauth_info function."""

    def test_extract_from_oauth_token_attribute(self) -> None:
        """Should extract token from request.oauth_token.token."""
        mock_request = MagicMock()
        mock_oauth_token = MagicMock()
        mock_oauth_token.token = "hf_test_token_123"
        mock_request.oauth_token = mock_oauth_token
        mock_request.username = "testuser"
        
        token, username = extract_oauth_info(mock_request)
        
        assert token == "hf_test_token_123"
        assert username == "testuser"

    def test_extract_from_string_oauth_token(self) -> None:
        """Should extract token when oauth_token is a string."""
        mock_request = MagicMock()
        mock_request.oauth_token = "hf_test_token_123"
        mock_request.username = "testuser"
        
        token, username = extract_oauth_info(mock_request)
        
        assert token == "hf_test_token_123"
        assert username == "testuser"

    def test_extract_from_authorization_header(self) -> None:
        """Should extract token from Authorization header."""
        mock_request = MagicMock()
        mock_request.oauth_token = None
        mock_request.headers = {"Authorization": "Bearer hf_test_token_123"}
        mock_request.username = "testuser"
        
        token, username = extract_oauth_info(mock_request)
        
        assert token == "hf_test_token_123"
        assert username == "testuser"

    def test_extract_username_from_oauth_profile(self) -> None:
        """Should extract username from oauth_profile."""
        mock_request = MagicMock()
        mock_request.oauth_token = None
        mock_request.username = None
        mock_oauth_profile = MagicMock()
        mock_oauth_profile.username = "testuser"
        mock_request.oauth_profile = mock_oauth_profile
        
        token, username = extract_oauth_info(mock_request)
        
        assert username == "testuser"

    def test_extract_name_from_oauth_profile(self) -> None:
        """Should extract name from oauth_profile when username not available."""
        mock_request = MagicMock()
        mock_request.oauth_token = None
        mock_request.username = None
        mock_oauth_profile = MagicMock()
        mock_oauth_profile.username = None
        mock_oauth_profile.name = "Test User"
        mock_request.oauth_profile = mock_oauth_profile
        
        token, username = extract_oauth_info(mock_request)
        
        assert username == "Test User"

    def test_extract_none_request(self) -> None:
        """Should return None for both when request is None."""
        token, username = extract_oauth_info(None)
        
        assert token is None
        assert username is None

    def test_extract_no_oauth_info(self) -> None:
        """Should return None when no OAuth info is available."""
        mock_request = MagicMock()
        mock_request.oauth_token = None
        mock_request.headers = {}
        mock_request.username = None
        mock_request.oauth_profile = None
        
        token, username = extract_oauth_info(mock_request)
        
        assert token is None
        assert username is None


class TestUpdateModelProviderDropdowns:
    """Tests for update_model_provider_dropdowns function."""

    @pytest.mark.asyncio
    async def test_update_with_valid_token(self) -> None:
        """Should update dropdowns with available models and providers."""
        mock_oauth_token = MagicMock()
        mock_oauth_token.token = "hf_test_token_123"
        mock_oauth_profile = MagicMock()
        
        mock_validation_result = {
            "is_valid": True,
            "has_inference_api_scope": True,
            "available_models": ["model1", "model2"],
            "available_providers": ["auto", "nebius"],
            "username": "testuser",
        }
        
        with patch("src.app.validate_oauth_token", return_value=mock_validation_result) as mock_validate, \
             patch("src.app.get_available_models", new_callable=AsyncMock) as mock_get_models, \
             patch("src.app.get_available_providers", new_callable=AsyncMock) as mock_get_providers, \
             patch("src.app.gr") as mock_gr, \
             patch("src.app.logger"):
            mock_get_models.return_value = ["model1", "model2"]
            mock_get_providers.return_value = ["auto", "nebius"]
            mock_gr.update.return_value = {"choices": [], "value": ""}
            
            result = await update_model_provider_dropdowns(mock_oauth_token, mock_oauth_profile)
            
            assert len(result) == 3  # model_update, provider_update, status_msg
            assert "testuser" in result[2]  # Status message should contain username
            mock_validate.assert_called_once_with("hf_test_token_123")

    @pytest.mark.asyncio
    async def test_update_with_no_token(self) -> None:
        """Should return defaults when no token provided."""
        with patch("src.app.gr") as mock_gr:
            mock_gr.update.return_value = {"choices": [], "value": ""}
            
            result = await update_model_provider_dropdowns(None, None)
            
            assert len(result) == 3
            assert "Not authenticated" in result[2]  # Status message

    @pytest.mark.asyncio
    async def test_update_with_invalid_token(self) -> None:
        """Should return error message for invalid token."""
        mock_oauth_token = MagicMock()
        mock_oauth_token.token = "invalid_token"
        
        mock_validation_result = {
            "is_valid": False,
            "error": "Invalid token format",
        }
        
        with patch("src.app.validate_oauth_token", return_value=mock_validation_result), \
             patch("src.app.gr") as mock_gr:
            mock_gr.update.return_value = {"choices": [], "value": ""}
            
            result = await update_model_provider_dropdowns(mock_oauth_token, None)
            
            assert len(result) == 3
            assert "Token validation failed" in result[2]

    @pytest.mark.asyncio
    async def test_update_without_inference_scope(self) -> None:
        """Should warn when token lacks inference-api scope."""
        mock_oauth_token = MagicMock()
        mock_oauth_token.token = "hf_token_without_scope"
        
        mock_validation_result = {
            "is_valid": True,
            "has_inference_api_scope": False,
            "available_models": [],
            "available_providers": ["auto"],
            "username": "testuser",
        }
        
        with patch("src.app.validate_oauth_token", return_value=mock_validation_result), \
             patch("src.app.get_available_models", new_callable=AsyncMock) as mock_get_models, \
             patch("src.app.get_available_providers", new_callable=AsyncMock) as mock_get_providers, \
             patch("src.app.gr") as mock_gr, \
             patch("src.app.logger"):
            mock_get_models.return_value = []
            mock_get_providers.return_value = ["auto"]
            mock_gr.update.return_value = {"choices": [], "value": ""}
            
            result = await update_model_provider_dropdowns(mock_oauth_token, None)
            
            assert len(result) == 3
            assert "inference-api scope" in result[2]

    @pytest.mark.asyncio
    async def test_update_handles_exception(self) -> None:
        """Should handle exceptions gracefully."""
        mock_oauth_token = MagicMock()
        mock_oauth_token.token = "hf_test_token"
        
        with patch("src.app.validate_oauth_token", side_effect=Exception("API error")), \
             patch("src.app.gr") as mock_gr, \
             patch("src.app.logger"):
            mock_gr.update.return_value = {"choices": [], "value": ""}
            
            result = await update_model_provider_dropdowns(mock_oauth_token, None)
            
            assert len(result) == 3
            assert "Failed to load models" in result[2]

    @pytest.mark.asyncio
    async def test_update_with_string_token(self) -> None:
        """Should handle string token (edge case)."""
        # Edge case: oauth_token is already a string
        with patch("src.app.validate_oauth_token") as mock_validate, \
             patch("src.app.get_available_models", new_callable=AsyncMock), \
             patch("src.app.get_available_providers", new_callable=AsyncMock), \
             patch("src.app.gr") as mock_gr, \
             patch("src.app.logger"):
            mock_validation_result = {
                "is_valid": True,
                "has_inference_api_scope": True,
                "available_models": ["model1"],
                "available_providers": ["auto"],
                "username": "testuser",
            }
            mock_validate.return_value = mock_validation_result
            mock_gr.update.return_value = {"choices": [], "value": ""}
            
            # Pass string directly (shouldn't happen but defensive)
            result = await update_model_provider_dropdowns("hf_string_token", None)
            
            # Should still work (extracts as string)
            assert len(result) == 3

