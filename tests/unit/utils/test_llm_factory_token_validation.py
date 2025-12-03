"""Unit tests for token validation in llm_factory.py."""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.exceptions import ConfigurationError


class TestGetPydanticAiModelTokenValidation:
    """Tests for get_pydantic_ai_model function with token validation."""

    @patch("src.utils.llm_factory.settings")
    @patch("src.utils.hf_error_handler.log_token_info")
    @patch("src.utils.hf_error_handler.validate_hf_token")
    @patch("pydantic_ai.providers.huggingface.HuggingFaceProvider")
    @patch("pydantic_ai.models.huggingface.HuggingFaceModel")
    def test_validates_oauth_token(
        self,
        mock_model_class,
        mock_provider_class,
        mock_validate,
        mock_log,
        mock_settings,
    ) -> None:
        """Should validate and log OAuth token when provided."""
        mock_settings.hf_token = None
        mock_settings.huggingface_api_key = None
        mock_settings.huggingface_model = "test-model"
        mock_validate.return_value = (True, None)
        mock_model_class.return_value = MagicMock()
        
        from src.utils.llm_factory import get_pydantic_ai_model
        
        get_pydantic_ai_model(oauth_token="hf_test_token")
        
        # Should log token info
        mock_log.assert_called_once_with("hf_test_token", context="get_pydantic_ai_model")
        # Should validate token
        mock_validate.assert_called_once_with("hf_test_token")

    @patch("src.utils.llm_factory.settings")
    @patch("src.utils.hf_error_handler.log_token_info")
    @patch("src.utils.hf_error_handler.validate_hf_token")
    @patch("src.utils.llm_factory.logger")
    @patch("pydantic_ai.providers.huggingface.HuggingFaceProvider")
    @patch("pydantic_ai.models.huggingface.HuggingFaceModel")
    def test_warns_on_invalid_token(
        self,
        mock_model_class,
        mock_provider_class,
        mock_logger,
        mock_validate,
        mock_log,
        mock_settings,
    ) -> None:
        """Should warn when token validation fails."""
        mock_settings.hf_token = None
        mock_settings.huggingface_api_key = None
        mock_settings.huggingface_model = "test-model"
        mock_validate.return_value = (False, "Token too short")
        mock_model_class.return_value = MagicMock()
        
        from src.utils.llm_factory import get_pydantic_ai_model
        
        get_pydantic_ai_model(oauth_token="short")
        
        # Should warn about invalid token
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "Token validation failed" in str(call)
        ]
        assert len(warning_calls) > 0

    @patch("src.utils.llm_factory.settings")
    @patch("src.utils.hf_error_handler.log_token_info")
    @patch("src.utils.hf_error_handler.validate_hf_token")
    @patch("pydantic_ai.providers.huggingface.HuggingFaceProvider")
    @patch("pydantic_ai.models.huggingface.HuggingFaceModel")
    def test_uses_env_token_when_oauth_not_provided(
        self,
        mock_model_class,
        mock_provider_class,
        mock_validate,
        mock_log,
        mock_settings,
    ) -> None:
        """Should use environment token when OAuth token not provided."""
        mock_settings.hf_token = "hf_env_token"
        mock_settings.huggingface_api_key = None
        mock_settings.huggingface_model = "test-model"
        mock_validate.return_value = (True, None)
        mock_model_class.return_value = MagicMock()
        
        from src.utils.llm_factory import get_pydantic_ai_model
        
        get_pydantic_ai_model(oauth_token=None)
        
        # Should log and validate env token
        mock_log.assert_called_once_with("hf_env_token", context="get_pydantic_ai_model")
        mock_validate.assert_called_once_with("hf_env_token")

    @patch("src.utils.llm_factory.settings")
    def test_raises_when_no_token_available(self, mock_settings) -> None:
        """Should raise ConfigurationError when no token is available."""
        mock_settings.hf_token = None
        mock_settings.huggingface_api_key = None
        
        from src.utils.llm_factory import get_pydantic_ai_model
        
        with pytest.raises(ConfigurationError, match="HuggingFace token required"):
            get_pydantic_ai_model(oauth_token=None)

    @patch("src.utils.llm_factory.settings")
    @patch("src.utils.hf_error_handler.log_token_info")
    @patch("src.utils.hf_error_handler.validate_hf_token")
    @patch("pydantic_ai.providers.huggingface.HuggingFaceProvider")
    @patch("pydantic_ai.models.huggingface.HuggingFaceModel")
    def test_oauth_token_priority_over_env(
        self,
        mock_model_class,
        mock_provider_class,
        mock_validate,
        mock_log,
        mock_settings,
    ) -> None:
        """Should prefer OAuth token over environment token."""
        mock_settings.hf_token = "hf_env_token"
        mock_settings.huggingface_api_key = None
        mock_settings.huggingface_model = "test-model"
        mock_validate.return_value = (True, None)
        mock_model_class.return_value = MagicMock()
        
        from src.utils.llm_factory import get_pydantic_ai_model
        
        get_pydantic_ai_model(oauth_token="hf_oauth_token")
        
        # Should use OAuth token, not env token
        mock_log.assert_called_once_with("hf_oauth_token", context="get_pydantic_ai_model")
        mock_validate.assert_called_once_with("hf_oauth_token")

