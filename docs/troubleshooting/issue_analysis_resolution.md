# Issue Analysis and Resolution Plan

## Executive Summary

This document analyzes the multiple issues observed in the application logs, identifies root causes, and provides a comprehensive resolution plan with file-level and line-level tasks.

## Issues Identified

### 0. Web Search Implementation Issues (FIXED ✅)

**Problems**:
1. DuckDuckGo used by default instead of Serper (even when Serper API key available)
2. Serper used invalid `source="serper"` (should be `source="web"`)
3. SearchXNG used invalid `source="searchxng"` (should be `source="web"`)
4. Serper and SearchXNG missing title truncation (would cause validation errors)
5. Missing tool name mappings in SearchHandler

**Root Causes**:
- Default `web_search_provider` was `"duckduckgo"` instead of `"auto"`
- No auto-detection logic to prefer Serper when API key available
- Source type mismatches with SourceName literal
- Missing title truncation in Serper/SearchXNG implementations

**Fixes Applied**:
- ✅ Changed default to `"auto"` with auto-detection logic
- ✅ Fixed Serper to use `source="web"` and add title truncation
- ✅ Fixed SearchXNG to use `source="web"` and add title truncation
- ✅ Added tool name mappings in SearchHandler
- ✅ Improved factory to auto-detect best available provider

**Status**: ✅ **FIXED** - All web search issues resolved

---

### 1. Citation Title Validation Error (FIXED ✅)

**Error**: `1 validation error for Citation\ntitle\n  String should have at most 500 characters`

**Root Cause**: DuckDuckGo search results can return titles longer than 500 characters, but the `Citation` model enforces a maximum length of 500 characters.

**Location**: `src/tools/web_search.py:61`

**Fix Applied**: Added title truncation to 500 characters before creating Citation objects.

**Status**: ✅ **FIXED** - Code updated in `src/tools/web_search.py`

---

### 2. 403 Forbidden Errors on HuggingFace Inference API

**Error**: `status_code: 403, model_name: Qwen/Qwen3-Next-80B-A3B-Thinking, body: Forbidden`

**Root Causes**:
1. **OAuth Scope Missing**: The OAuth token may not have the `inference-api` scope required for accessing HuggingFace Inference API
2. **Model Access Restrictions**: Some models (e.g., `Qwen/Qwen3-Next-80B-A3B-Thinking`) may require:
   - Gated model access approval
   - Specific provider access
   - Account-level permissions
3. **Provider Selection**: Pydantic AI's `HuggingFaceProvider` doesn't support explicit provider selection (e.g., "nebius", "hyperbolic"), which may be required for certain models
4. **Token Format**: The OAuth token might not be correctly extracted or formatted

**Evidence from Logs**:
- OAuth authentication succeeds: `OAuth user authenticated username=Tonic`
- Token is extracted: `OAuth token extracted from oauth_token.token attribute`
- But API calls fail: `status_code: 403, model_name: Qwen/Qwen3-Next-80B-A3B-Thinking, body: Forbidden`

**Impact**: All LLM operations fail, causing:
- Planner agent execution failures
- Observation generation failures
- Knowledge gap evaluation failures
- Tool selection failures
- Judge assessment failures
- Report writing failures

**Status**: ⚠️ **INVESTIGATION REQUIRED**

---

### 3. 422 Unprocessable Entity Errors

**Error**: `status_code: 422, model_name: meta-llama/Llama-3.1-70B-Instruct, body: Unprocessable Entity`

**Root Cause**: 
- Model/provider compatibility issues
- The model `meta-llama/Llama-3.1-70B-Instruct` on provider `hyperbolic` may be in staging mode or have specific requirements
- Request format may not match provider expectations

**Evidence from Logs**:
- `Model meta-llama/Llama-3.1-70B-Instruct is in staging mode for provider hyperbolic. Meant for test purposes only.`
- Followed by: `status_code: 422, model_name: meta-llama/Llama-3.1-70B-Instruct, body: Unprocessable Entity`

**Impact**: Judge assessment fails, causing research loops to continue indefinitely with low confidence scores.

**Status**: ⚠️ **INVESTIGATION REQUIRED**

---

### 4. MCP Server Warning

**Warning**: `This MCP server includes a tool that has a gr.State input, which will not be updated between tool calls.`

**Root Cause**: Gradio MCP integration issue with state management.

**Impact**: Minor - functionality may be affected but not critical.

**Status**: ℹ️ **INFORMATIONAL**

---

### 5. Modal TTS Function Setup Failure

**Error**: `modal_tts_function_setup_failed error='Local state is not initialized - app is not locally available'`

**Root Cause**: Modal TTS function requires local Modal app initialization, which isn't available in HuggingFace Spaces environment.

**Impact**: Text-to-speech functionality unavailable, but not critical for core functionality.

**Status**: ℹ️ **INFORMATIONAL**

---

## Root Cause Analysis

### OAuth Token Flow

1. **Token Extraction** (`src/app.py:617-628`):
   ```python
   if hasattr(oauth_token, "token"):
       token_value = oauth_token.token
   ```
   ✅ **Working correctly** - Logs confirm token extraction

2. **Token Passing** (`src/app.py:125`, `src/agent_factory/judges.py:54`):
   ```python
   effective_api_key = oauth_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
   hf_provider = HuggingFaceProvider(api_key=effective_api_key)
   ```
   ✅ **Working correctly** - Token is passed to HuggingFaceProvider

3. **API Calls** (Pydantic AI internal):
   - Pydantic AI's `HuggingFaceProvider` uses `AsyncInferenceClient` internally
   - The `api_key` parameter should be passed to the underlying client
   - ❓ **Unknown**: Whether the token format or scope is correct

### HuggingFaceProvider Limitations

**Key Finding**: The code comments indicate:
```python
# Note: The hf_provider parameter is accepted but not used here because HuggingFaceProvider
# from pydantic-ai doesn't support provider selection. Provider selection happens at the
# InferenceClient level (used in HuggingFaceChatClient for advanced mode).
```

This means:
- `HuggingFaceProvider` doesn't support explicit provider selection (e.g., "nebius", "hyperbolic")
- Provider selection is automatic or uses default HuggingFace Inference API endpoint
- Some models may require specific providers, which can't be specified

### Model Access Issues

The logs show attempts to use:
- `Qwen/Qwen3-Next-80B-A3B-Thinking` - May require gated access
- `meta-llama/Llama-3.1-70B-Instruct` - May have provider-specific restrictions
- `Qwen/Qwen3-235B-A22B-Instruct-2507` - May require special permissions

---

## Resolution Plan

### Phase 1: Immediate Fixes (Completed)

✅ **Task 1.1**: Fix Citation title validation error
- **File**: `src/tools/web_search.py`
- **Line**: 60-61
- **Change**: Add title truncation to 500 characters
- **Status**: ✅ **COMPLETED**

---

### Phase 2: OAuth Token Investigation and Fixes

#### Task 2.1: Add Token Validation and Debugging

**Files to Modify**:
- `src/utils/llm_factory.py`
- `src/agent_factory/judges.py`
- `src/app.py`

**Subtasks**:
1. Add token format validation (check if token is a valid string)
2. Add token length logging (without exposing actual token)
3. Add scope verification (if possible via API)
4. Add detailed error logging for 403 errors

**Line-Level Tasks**:
- `src/utils/llm_factory.py:139`: Add token validation before creating HuggingFaceProvider
- `src/agent_factory/judges.py:54`: Add token validation and logging
- `src/app.py:125`: Add token format validation

#### Task 2.2: Improve Error Handling for 403 Errors

**Files to Modify**:
- `src/agent_factory/judges.py`
- `src/agents/*.py` (all agent files)

**Subtasks**:
1. Catch `ModelHTTPError` with status_code 403 specifically
2. Provide user-friendly error messages
3. Suggest solutions (re-authenticate, check scope, use alternative model)
4. Log detailed error information for debugging

**Line-Level Tasks**:
- `src/agent_factory/judges.py:159`: Add specific 403 error handling
- `src/agents/knowledge_gap.py`: Add error handling in agent execution
- `src/agents/tool_selector.py`: Add error handling in agent execution
- `src/agents/thinking.py`: Add error handling in agent execution
- `src/agents/writer.py`: Add error handling in agent execution

#### Task 2.3: Add Fallback Mechanisms

**Files to Modify**:
- `src/agent_factory/judges.py`
- `src/utils/llm_factory.py`

**Subtasks**:
1. Define fallback model list (publicly available models)
2. Implement automatic fallback when primary model fails with 403
3. Log fallback model selection
4. Continue with fallback model if available

**Line-Level Tasks**:
- `src/agent_factory/judges.py:30-66`: Add fallback model logic in `get_model()`
- `src/utils/llm_factory.py:121-153`: Add fallback model logic in `get_pydantic_ai_model()`

#### Task 2.4: Document OAuth Scope Requirements

**Files to Create/Modify**:
- `docs/troubleshooting/oauth_403_errors.md` ✅ **CREATED**
- `README.md`: Add OAuth setup instructions
- `src/app.py:114-120`: Enhance existing comments

**Subtasks**:
1. Document required OAuth scopes
2. Provide troubleshooting steps
3. Add examples of correct OAuth configuration
4. Link to HuggingFace documentation

---

### Phase 3: 422 Error Handling

#### Task 3.1: Add 422 Error Handling

**Files to Modify**:
- `src/agent_factory/judges.py`
- `src/utils/llm_factory.py`

**Subtasks**:
1. Catch 422 errors specifically
2. Detect staging mode warnings
3. Automatically switch to alternative provider or model
4. Log provider/model compatibility issues

**Line-Level Tasks**:
- `src/agent_factory/judges.py:159`: Add 422 error handling
- `src/utils/llm_factory.py`: Add provider fallback logic

#### Task 3.2: Provider Selection Enhancement

**Files to Modify**:
- `src/utils/huggingface_chat_client.py`
- `src/app.py`

**Subtasks**:
1. Investigate if HuggingFaceProvider can be configured with provider
2. If not, use HuggingFaceChatClient for provider selection
3. Add provider fallback chain
4. Log provider selection and failures

**Line-Level Tasks**:
- `src/utils/huggingface_chat_client.py:29-64`: Enhance provider selection
- `src/app.py:154`: Consider using HuggingFaceChatClient for provider support

---

### Phase 4: Enhanced Logging and Monitoring

#### Task 4.1: Add Comprehensive Error Logging

**Files to Modify**:
- All agent files
- `src/agent_factory/judges.py`
- `src/utils/llm_factory.py`

**Subtasks**:
1. Log token presence (not value) at key points
2. Log model selection and provider
3. Log HTTP status codes and error bodies
4. Log fallback attempts and results

#### Task 4.2: Add User-Friendly Error Messages

**Files to Modify**:
- `src/app.py`
- `src/orchestrator/graph_orchestrator.py`

**Subtasks**:
1. Convert technical errors to user-friendly messages
2. Provide actionable solutions
3. Link to documentation
4. Suggest alternative models or configurations

---

## Implementation Priority

### High Priority (Blocking Issues)
1. ✅ Citation title validation (COMPLETED)
2. OAuth token validation and debugging
3. 403 error handling with fallback
4. User-friendly error messages

### Medium Priority (Quality Improvements)
5. 422 error handling
6. Provider selection enhancement
7. Comprehensive logging

### Low Priority (Nice to Have)
8. MCP server warning fix
9. Modal TTS setup (environment-specific)

---

## Testing Plan

### Unit Tests
- Test Citation title truncation with various lengths
- Test token validation logic
- Test fallback model selection
- Test error handling for 403, 422 errors

### Integration Tests
- Test OAuth token flow end-to-end
- Test model fallback chain
- Test provider selection
- Test error recovery

### Manual Testing
- Verify OAuth login with correct scope
- Test with various models
- Test error scenarios
- Verify user-friendly error messages

---

## Success Criteria

1. ✅ Citation validation errors eliminated
2. 403 errors handled gracefully with fallback
3. 422 errors handled with provider/model fallback
4. Clear error messages for users
5. Comprehensive logging for debugging
6. Documentation updated with troubleshooting steps

---

## References

- [HuggingFace OAuth Scopes](https://huggingface.co/docs/hub/oauth#currently-supported-scopes)
- [Pydantic AI HuggingFace Provider](https://ai.pydantic.dev/models/huggingface/)
- [HuggingFace Inference API](https://huggingface.co/docs/api-inference/index)
- [HuggingFace Inference Providers](https://huggingface.co/docs/api-inference/inference_providers)

