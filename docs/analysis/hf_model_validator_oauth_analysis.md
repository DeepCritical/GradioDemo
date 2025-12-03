# HuggingFace Model Validator OAuth & API Analysis

## Executive Summary

This document analyzes the feasibility of improving OAuth integration and provider discovery in `src/utils/hf_model_validator.py` (lines 49-58), based on available Gradio OAuth features and Hugging Face Hub API capabilities.

## Current Implementation Issues

### 1. Non-Existent API Endpoint
**Problem**: Lines 61-64 attempt to query `https://api-inference.huggingface.co/providers`, which does not exist.

**Evidence**: 
- No documentation for this endpoint
- The code already has a fallback to hardcoded providers
- Hugging Face Hub API documentation shows no such endpoint

**Impact**: Unnecessary API call that always fails, adding latency and error noise.

### 2. Hardcoded Provider List
**Problem**: Lines 36-48 maintain a static list of providers that may become outdated.

**Current List**: `["auto", "nebius", "together", "scaleway", "hyperbolic", "novita", "nscale", "sambanova", "ovh", "fireworks", "cerebras"]`

**Impact**: New providers won't be discovered automatically, requiring manual code updates.

### 3. Limited OAuth Token Utilization
**Problem**: While the function accepts OAuth tokens, it doesn't fully leverage them for provider discovery.

**Current State**: Token is passed to API calls but not used to discover providers dynamically.

## Available OAuth Features

### Gradio OAuth Integration

1. **`gr.LoginButton`**: Enables "Sign in with Hugging Face" in Spaces
2. **`gr.OAuthToken`**: Automatically passed to functions when user is logged in
   - Has `.token` attribute containing the access token
   - Is `None` when user is not logged in
3. **`gr.OAuthProfile`**: Contains user profile information
   - `.username`: Hugging Face username
   - `.name`: Display name
   - `.profile_image`: Profile image URL

### OAuth Token Scopes

According to Hugging Face documentation:
- **`inference-api` scope**: Required for accessing Inference Providers API
- Grants access to:
  - HuggingFace's own Inference API
  - All third-party inference providers (nebius, together, scaleway, etc.)
  - All models available through the Inference Providers API

**Reference**: https://huggingface.co/docs/hub/oauth#currently-supported-scopes

## Available Hugging Face Hub API Endpoints

### 1. List Models by Provider
**Endpoint**: `HfApi.list_models(inference_provider="provider_name")`

**Usage**:
```python
from huggingface_hub import HfApi
api = HfApi(token=token)
models = api.list_models(inference_provider="fireworks-ai", task="text-generation")
```

**Capabilities**:
- Filter models by specific provider
- Filter by task type
- Support multiple providers: `inference_provider=["fireworks-ai", "together"]`
- Get all provider-served models: `inference_provider="all"`

### 2. Get Model Provider Mapping
**Endpoint**: `HfApi.model_info(model_id, expand="inferenceProviderMapping")`

**Usage**:
```python
from huggingface_hub import model_info
info = model_info("google/gemma-3-27b-it", expand="inferenceProviderMapping")
providers = info.inference_provider_mapping
# Returns: {'hf-inference': InferenceProviderMapping(...), 'nebius': ...}
```

**Capabilities**:
- Get all providers serving a specific model
- Includes provider status (`live` or `staging`)
- Includes provider-specific model ID

### 3. List All Provider-Served Models
**Endpoint**: `HfApi.list_models(inference_provider="all")`

**Usage**:
```python
models = api.list_models(inference_provider="all", task="text-generation", limit=100)
```

**Capabilities**:
- Get all models served by any provider
- Can extract unique providers from model metadata

## Feasibility Assessment

### ✅ Feasible Improvements

1. **Dynamic Provider Discovery**
   - **Method**: Query models with `inference_provider="all"` and extract unique providers from model info
   - **Limitation**: Requires querying multiple models, which can be slow
   - **Alternative**: Use a hybrid approach: query a sample of popular models and extract providers

2. **OAuth Token Integration**
   - **Method**: Extract token from `gr.OAuthToken.token` attribute
   - **Status**: Already implemented in `src/app.py` (lines 384-408)
   - **Enhancement**: Better error handling and scope validation

3. **Provider Validation**
   - **Method**: Use `model_info(expand="inferenceProviderMapping")` to validate model/provider combinations
   - **Status**: Partially implemented in `validate_model_provider_combination()`
   - **Enhancement**: Use provider mapping instead of test API calls

### ⚠️ Limitations

1. **No Public Provider List API**
   - There is no public endpoint to list all available providers
   - Must discover providers indirectly through model queries

2. **Performance Considerations**
   - Querying many models to discover providers can be slow
   - Caching is essential for good user experience

3. **Provider Name Variations**
   - Provider names in API may differ from display names
   - Some providers may use different identifiers (e.g., "fireworks-ai" vs "fireworks")

## Proposed Improvements

### 1. Dynamic Provider Discovery

**Approach**: Query a sample of popular models and extract unique providers from their `inferenceProviderMapping`.

**Implementation**:
```python
async def get_available_providers(token: str | None = None) -> list[str]:
    """Get list of available inference providers dynamically."""
    try:
        # Query popular models to discover providers
        popular_models = [
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "google/gemma-2-9b-it",
            "deepseek-ai/DeepSeek-V3-0324",
        ]
        
        providers = set(["auto"])  # Always include "auto"
        
        loop = asyncio.get_running_loop()
        api = HfApi(token=token)
        
        for model_id in popular_models:
            try:
                info = await loop.run_in_executor(
                    None,
                    lambda m=model_id: api.model_info(m, expand="inferenceProviderMapping"),
                )
                if hasattr(info, "inference_provider_mapping") and info.inference_provider_mapping:
                    providers.update(info.inference_provider_mapping.keys())
            except Exception:
                continue
        
        # Fallback to known providers if discovery fails
        if len(providers) <= 1:  # Only "auto"
            providers.update(KNOWN_PROVIDERS)
        
        return sorted(list(providers))
    except Exception:
        return KNOWN_PROVIDERS
```

### 2. Enhanced OAuth Token Handling

**Improvements**:
- Add helper function to extract token from `gr.OAuthToken`
- Validate token scope using `api.whoami()` and inference API test
- Better error messages for missing scopes

### 3. Caching Strategy

**Implementation**:
- Cache provider list for 1 hour (providers don't change frequently)
- Cache model lists per provider for 30 minutes
- Invalidate cache on authentication changes

### 4. Provider Validation Enhancement

**Current**: Makes test API calls (slow, unreliable)

**Proposed**: Use `model_info(expand="inferenceProviderMapping")` to check if provider is listed for the model.

## Implementation Priority

1. **High Priority**: Remove non-existent API endpoint call (lines 58-73)
2. **High Priority**: Add caching for provider discovery
3. **Medium Priority**: Implement dynamic provider discovery
4. **Medium Priority**: Enhance OAuth token validation
5. **Low Priority**: Add provider status (live/staging) information

## References

- [Hugging Face OAuth Documentation](https://huggingface.co/docs/hub/oauth)
- [Gradio LoginButton Documentation](https://www.gradio.app/docs/gradio/loginbutton)
- [Hugging Face Hub API - Inference Providers](https://huggingface.co/docs/inference-providers/hub-api)
- [Hugging Face Hub Python Client](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api)

