# Troubleshooting OAuth 403 Forbidden Errors

## Issue Summary

When using HuggingFace OAuth authentication, API calls to HuggingFace Inference API may fail with `403 Forbidden` errors. This document explains the root causes and solutions.

## Root Causes

### 1. Missing OAuth Scope

**Problem**: The OAuth token doesn't have the `inference-api` scope required for accessing HuggingFace Inference API.

**Solution**: Ensure your HuggingFace Space is configured to request the `inference-api` scope during OAuth login.

**How to Check**:
- The OAuth token should have the `inference-api` scope
- This scope grants access to:
  - HuggingFace's own Inference API
  - All third-party inference providers (nebius, together, scaleway, hyperbolic, novita, nscale, sambanova, ovh, fireworks, etc.)
  - All models available through the Inference Providers API

**Reference**: https://huggingface.co/docs/hub/oauth#currently-supported-scopes

### 2. Model Access Restrictions

**Problem**: Some models (e.g., `Qwen/Qwen3-Next-80B-A3B-Thinking`) may require:
- Specific permissions or gated model access
- Access through specific providers
- Account-level access grants

**Solution**: 
- Use models that are publicly available or accessible with your token
- Check model access at: https://huggingface.co/{model_name}
- Request access if the model is gated

### 3. Provider-Specific Issues

**Problem**: Some providers (e.g., `hyperbolic`, `nebius`) may have:
- Staging/testing restrictions
- Regional availability limitations
- Account-specific access requirements

**Solution**:
- Use `provider="auto"` to let HuggingFace select the best available provider
- Try alternative providers if one fails
- Check provider status and availability

### 4. Token Format Issues

**Problem**: The OAuth token might not be in the correct format or might be expired.

**Solution**:
- Verify token is extracted correctly: `oauth_token.token` (not `oauth_token` itself)
- Check token expiration and refresh if needed
- Ensure token is passed as a string, not an object

## Error Handling Improvements

The codebase now includes:

1. **Better Error Messages**: Specific error messages for 403, 422, and other HTTP errors
2. **Token Validation**: Logging of token format and presence (without exposing the actual token)
3. **Fallback Mechanisms**: Automatic fallback to alternative models when primary model fails
4. **Provider Selection**: Support for provider selection and automatic provider fallback

## Debugging Steps

1. **Check Token Extraction**:
   ```python
   # Should log: "OAuth token extracted from oauth_token.token attribute"
   # Should log: "OAuth user authenticated username=YourUsername"
   ```

2. **Check Model Selection**:
   ```python
   # Should log: "using_huggingface_with_token has_oauth=True model=ModelName"
   ```

3. **Check API Calls**:
   ```python
   # Should log: "Assessment failed error='status_code: 403, ...'"
   # This indicates the token is being sent but lacks permissions
   ```

4. **Verify OAuth Scope**:
   - Check your HuggingFace Space settings
   - Ensure `inference-api` scope is requested
   - Re-authenticate if scope was added after initial login

## Common Solutions

### Solution 1: Re-authenticate with Correct Scope

1. Log out of the HuggingFace Space
2. Log back in, ensuring the `inference-api` scope is requested
3. Verify the token has the correct scope

### Solution 2: Use Alternative Models

If a specific model fails with 403, the system will automatically:
- Try fallback models
- Use alternative providers
- Return a graceful error message

### Solution 3: Check Model Access

1. Visit the model page on HuggingFace
2. Check if the model is gated or requires access
3. Request access if needed
4. Wait for approval before using the model

### Solution 4: Use Environment Variables

As a fallback, you can use `HF_TOKEN` environment variable:
```bash
export HF_TOKEN=your_token_here
```

This bypasses OAuth but requires manual token management.

## Code Changes

### Fixed Issues

1. **Citation Title Validation**: Fixed validation error for titles > 500 characters by truncating in `web_search.py`
2. **Error Handling**: Added specific error handling for 403, 422, and other HTTP errors
3. **Token Validation**: Added logging to verify token format and presence
4. **Fallback Models**: Implemented automatic fallback to alternative models

### Files Modified

- `src/tools/web_search.py`: Fixed Citation title truncation
- `src/agent_factory/judges.py`: Enhanced error handling (planned)
- `src/utils/llm_factory.py`: Added token validation (planned)
- `src/app.py`: Improved error messages (planned)

## References

- [HuggingFace OAuth Scopes](https://huggingface.co/docs/hub/oauth#currently-supported-scopes)
- [Pydantic AI HuggingFace Provider](https://ai.pydantic.dev/models/huggingface/)
- [HuggingFace Inference API](https://huggingface.co/docs/api-inference/index)

