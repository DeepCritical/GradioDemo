"""Unit tests for HuggingFace model and provider validator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.hf_model_validator import (
    extract_oauth_token,
    get_available_models,
    get_available_providers,
    get_models_for_provider,
    validate_model_provider_combination,
    validate_oauth_token,
)


class TestExtractOAuthToken:
    """Tests for extract_oauth_token function."""

    def test_extract_from_oauth_token_object(self) -> None:
        """Should extract token from OAuthToken object with .token attribute."""
        mock_oauth_token = MagicMock()
        mock_oauth_token.token = "hf_test_token_123"
        
        result = extract_oauth_token(mock_oauth_token)
        
        assert result == "hf_test_token_123"

    def test_extract_from_string(self) -> None:
        """Should return string token as-is."""
        token = "hf_test_token_123"
        result = extract_oauth_token(token)
        
        assert result == token

    def test_extract_none(self) -> None:
        """Should return None for None input."""
        result = extract_oauth_token(None)
        
        assert result is None

    def test_extract_invalid_object(self) -> None:
        """Should return None for object without .token attribute."""
        invalid_object = MagicMock()
        del invalid_object.token  # Remove token attribute
        
        with patch("src.utils.hf_model_validator.logger") as mock_logger:
            result = extract_oauth_token(invalid_object)
            
            assert result is None
            mock_logger.warning.assert_called_once()


class TestGetAvailableProviders:
    """Tests for get_available_providers function."""

    @pytest.mark.asyncio
    async def test_get_providers_with_cache(self) -> None:
        """Should return cached providers if available."""
        # First call - should query API
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            
            # Mock model_info to return provider mapping
            mock_model_info = MagicMock()
            mock_model_info.inference_provider_mapping = {
                "hf-inference": MagicMock(),
                "nebius": MagicMock(),
            }
            mock_api.model_info.return_value = mock_model_info
            
            # Mock settings
            with patch("src.utils.hf_model_validator.settings") as mock_settings:
                mock_settings.get_hf_fallback_models_list.return_value = [
                    "meta-llama/Llama-3.1-8B-Instruct"
                ]
                
                providers = await get_available_providers(token="test_token")
                
                assert "auto" in providers
                assert len(providers) > 1

    @pytest.mark.asyncio
    async def test_get_providers_fallback_to_known(self) -> None:
        """Should fall back to known providers if discovery fails."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            mock_api.model_info.side_effect = Exception("API error")
            
            with patch("src.utils.hf_model_validator.settings") as mock_settings:
                mock_settings.get_hf_fallback_models_list.return_value = [
                    "meta-llama/Llama-3.1-8B-Instruct"
                ]
                
                providers = await get_available_providers(token="test_token")
                
                # Should return known providers as fallback
                assert "auto" in providers
                assert len(providers) > 0

    @pytest.mark.asyncio
    async def test_get_providers_no_token(self) -> None:
        """Should work without token."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            mock_api.model_info.side_effect = Exception("API error")
            
            with patch("src.utils.hf_model_validator.settings") as mock_settings:
                mock_settings.get_hf_fallback_models_list.return_value = [
                    "meta-llama/Llama-3.1-8B-Instruct"
                ]
                
                providers = await get_available_providers(token=None)
                
                # Should return known providers as fallback
                assert "auto" in providers


class TestGetAvailableModels:
    """Tests for get_available_models function."""

    @pytest.mark.asyncio
    async def test_get_models_with_token(self) -> None:
        """Should fetch models with token."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            
            # Mock list_models to return model objects
            mock_model1 = MagicMock()
            mock_model1.id = "model1"
            mock_model2 = MagicMock()
            mock_model2.id = "model2"
            mock_api.list_models.return_value = [mock_model1, mock_model2]
            
            models = await get_available_models(token="test_token", limit=10)
            
            assert len(models) == 2
            assert "model1" in models
            assert "model2" in models
            mock_api.list_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_models_with_provider_filter(self) -> None:
        """Should filter models by provider."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            
            mock_model = MagicMock()
            mock_model.id = "model1"
            mock_api.list_models.return_value = [mock_model]
            
            models = await get_available_models(
                token="test_token",
                inference_provider="nebius",
                limit=10,
            )
            
            # Check that inference_provider was passed to list_models
            call_kwargs = mock_api.list_models.call_args[1]
            assert call_kwargs.get("inference_provider") == "nebius"

    @pytest.mark.asyncio
    async def test_get_models_fallback_on_error(self) -> None:
        """Should return fallback models on error."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            mock_api.list_models.side_effect = Exception("API error")
            
            models = await get_available_models(token="test_token", limit=10)
            
            # Should return fallback models
            assert len(models) > 0
            assert "meta-llama/Llama-3.1-8B-Instruct" in models


class TestValidateModelProviderCombination:
    """Tests for validate_model_provider_combination function."""

    @pytest.mark.asyncio
    async def test_validate_auto_provider(self) -> None:
        """Should always validate 'auto' provider."""
        is_valid, error_msg = await validate_model_provider_combination(
            model_id="test-model",
            provider="auto",
            token="test_token",
        )
        
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_validate_none_provider(self) -> None:
        """Should validate None provider as auto."""
        is_valid, error_msg = await validate_model_provider_combination(
            model_id="test-model",
            provider=None,
            token="test_token",
        )
        
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_validate_valid_combination(self) -> None:
        """Should validate valid model/provider combination."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            
            # Mock model_info with provider mapping
            mock_model_info = MagicMock()
            mock_model_info.inference_provider_mapping = {
                "nebius": MagicMock(),
                "hf-inference": MagicMock(),
            }
            mock_api.model_info.return_value = mock_model_info
            
            is_valid, error_msg = await validate_model_provider_combination(
                model_id="test-model",
                provider="nebius",
                token="test_token",
            )
            
            assert is_valid is True
            assert error_msg is None

    @pytest.mark.asyncio
    async def test_validate_invalid_combination(self) -> None:
        """Should reject invalid model/provider combination."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            
            # Mock model_info with provider mapping (without requested provider)
            mock_model_info = MagicMock()
            mock_model_info.inference_provider_mapping = {
                "hf-inference": MagicMock(),
            }
            mock_api.model_info.return_value = mock_model_info
            
            is_valid, error_msg = await validate_model_provider_combination(
                model_id="test-model",
                provider="nebius",
                token="test_token",
            )
            
            assert is_valid is False
            assert error_msg is not None
            assert "nebius" in error_msg

    @pytest.mark.asyncio
    async def test_validate_fireworks_variants(self) -> None:
        """Should handle fireworks/fireworks-ai name variants."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            
            # Mock model_info with fireworks-ai in mapping
            mock_model_info = MagicMock()
            mock_model_info.inference_provider_mapping = {
                "fireworks-ai": MagicMock(),
            }
            mock_api.model_info.return_value = mock_model_info
            
            # Should accept "fireworks" when mapping has "fireworks-ai"
            is_valid, error_msg = await validate_model_provider_combination(
                model_id="test-model",
                provider="fireworks",
                token="test_token",
            )
            
            assert is_valid is True
            assert error_msg is None

    @pytest.mark.asyncio
    async def test_validate_graceful_on_error(self) -> None:
        """Should return valid on error (graceful degradation)."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            mock_api.model_info.side_effect = Exception("API error")
            
            is_valid, error_msg = await validate_model_provider_combination(
                model_id="test-model",
                provider="nebius",
                token="test_token",
            )
            
            # Should return True to allow actual request to determine validity
            assert is_valid is True


class TestGetModelsForProvider:
    """Tests for get_models_for_provider function."""

    @pytest.mark.asyncio
    async def test_get_models_for_provider(self) -> None:
        """Should get models for specific provider."""
        with patch("src.utils.hf_model_validator.get_available_models") as mock_get_models:
            mock_get_models.return_value = ["model1", "model2"]
            
            models = await get_models_for_provider(
                provider="nebius",
                token="test_token",
                limit=10,
            )
            
            assert len(models) == 2
            mock_get_models.assert_called_once_with(
                token="test_token",
                task="text-generation",
                limit=10,
                inference_provider="nebius",
            )

    @pytest.mark.asyncio
    async def test_get_models_normalize_fireworks(self) -> None:
        """Should normalize 'fireworks' to 'fireworks-ai'."""
        with patch("src.utils.hf_model_validator.get_available_models") as mock_get_models:
            mock_get_models.return_value = ["model1"]
            
            models = await get_models_for_provider(
                provider="fireworks",
                token="test_token",
            )
            
            # Should call with "fireworks-ai" not "fireworks"
            call_kwargs = mock_get_models.call_args[1]
            assert call_kwargs["inference_provider"] == "fireworks-ai"


class TestValidateOAuthToken:
    """Tests for validate_oauth_token function."""

    @pytest.mark.asyncio
    async def test_validate_none_token(self) -> None:
        """Should return invalid for None token."""
        result = await validate_oauth_token(None)
        
        assert result["is_valid"] is False
        assert result["error"] == "No token provided"

    @pytest.mark.asyncio
    async def test_validate_invalid_format(self) -> None:
        """Should return invalid for malformed token."""
        result = await validate_oauth_token("short")
        
        assert result["is_valid"] is False
        assert "Invalid token format" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_valid_token(self) -> None:
        """Should validate valid token and return resources."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            
            # Mock whoami to return user info
            mock_api.whoami.return_value = {"name": "testuser", "fullname": "Test User"}
            
            # Mock get_available_models and get_available_providers
            with patch("src.utils.hf_model_validator.get_available_models") as mock_get_models, \
                 patch("src.utils.hf_model_validator.get_available_providers") as mock_get_providers:
                mock_get_models.return_value = ["model1", "model2"]
                mock_get_providers.return_value = ["auto", "nebius"]
                
                result = await validate_oauth_token("hf_valid_token_123")
                
                assert result["is_valid"] is True
                assert result["username"] == "testuser"
                assert result["has_inference_api_scope"] is True
                assert len(result["available_models"]) == 2
                assert len(result["available_providers"]) == 2

    @pytest.mark.asyncio
    async def test_validate_token_without_scope(self) -> None:
        """Should detect missing inference-api scope."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            mock_api.whoami.return_value = {"name": "testuser"}
            
            # Mock get_available_models to fail (no scope)
            with patch("src.utils.hf_model_validator.get_available_models") as mock_get_models, \
                 patch("src.utils.hf_model_validator.get_available_providers") as mock_get_providers:
                mock_get_models.side_effect = Exception("403 Forbidden")
                mock_get_providers.return_value = ["auto"]
                
                result = await validate_oauth_token("hf_token_without_scope")
                
                assert result["is_valid"] is True  # Token is valid
                assert result["has_inference_api_scope"] is False  # But no scope
                assert "inference-api scope" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_invalid_token(self) -> None:
        """Should return invalid for token that fails authentication."""
        with patch("src.utils.hf_model_validator.HfApi") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            mock_api.whoami.side_effect = Exception("401 Unauthorized")
            
            result = await validate_oauth_token("hf_invalid_token")
            
            assert result["is_valid"] is False
            assert "could not authenticate" in result["error"]



