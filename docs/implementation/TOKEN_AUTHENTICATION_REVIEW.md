# Token Authentication Review - Gradio & HuggingFace

## Summary

This document reviews the implementation of token authentication for Gradio Client API calls and HuggingFace API usage to ensure tokens are always passed correctly.

## ✅ Implementation Status

### 1. Gradio Client Services

#### STT Service (`src/services/stt_gradio.py`)
- ✅ **Token Support**: Service accepts `hf_token` parameter in `__init__` and methods
- ✅ **Client Initialization**: `Client` is created with `hf_token` parameter when token is available
- ✅ **Token Priority**: Method-level token > instance-level token
- ✅ **Token Updates**: Client is recreated if token changes

**Implementation Pattern:**
```python
async def _get_client(self, hf_token: str | None = None) -> Client:
    token = hf_token or self.hf_token
    if token:
        self.client = Client(self.api_url, hf_token=token)
    else:
        self.client = Client(self.api_url)
```

#### Image OCR Service (`src/services/image_ocr.py`)
- ✅ **Token Support**: Service accepts `hf_token` parameter in `__init__` and methods
- ✅ **Client Initialization**: `Client` is created with `hf_token` parameter when token is available
- ✅ **Token Priority**: Method-level token > instance-level token
- ✅ **Token Updates**: Client is recreated if token changes

**Same pattern as STT Service**

### 2. Service Layer Integration

#### Audio Service (`src/services/audio_processing.py`)
- ✅ **Token Passthrough**: `process_audio_input()` accepts `hf_token` and passes to STT service
- ✅ **Token Flow**: `audio_service.process_audio_input(audio, hf_token=token)`

#### Multimodal Service (`src/services/multimodal_processing.py`)
- ✅ **Token Passthrough**: `process_multimodal_input()` accepts `hf_token` and passes to both audio and OCR services
- ✅ **Token Flow**: `multimodal_service.process_multimodal_input(..., hf_token=token)`

### 3. Application Layer (`src/app.py`)

#### Token Extraction
- ✅ **OAuth Token**: Extracted from `gr.OAuthToken` via `oauth_token.token`
- ✅ **Fallback**: Uses `HF_TOKEN` or `HUGGINGFACE_API_KEY` from environment
- ✅ **Token Priority**: `oauth_token > HF_TOKEN > HUGGINGFACE_API_KEY`

**Implementation:**
```python
token_value: str | None = None
if oauth_token is not None:
    token_value = oauth_token.token if hasattr(oauth_token, "token") else None

# Fallback to env vars
effective_token = token_value or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
```

#### Token Usage in Services
- ✅ **Multimodal Processing**: Token passed to `process_multimodal_input(..., hf_token=token_value)`
- ✅ **Consistent Usage**: Token is extracted once and passed through all service layers

### 4. HuggingFace API Integration

#### LLM Factory (`src/utils/llm_factory.py`)
- ✅ **Token Priority**: `oauth_token > settings.hf_token > settings.huggingface_api_key`
- ✅ **Provider Usage**: `HuggingFaceProvider(api_key=effective_hf_token)`
- ✅ **Model Usage**: `HuggingFaceModel(model_name, provider=provider)`

#### Judge Handler (`src/agent_factory/judges.py`)
- ✅ **Token Priority**: `oauth_token > settings.hf_token > settings.huggingface_api_key`
- ✅ **InferenceClient**: `InferenceClient(api_key=api_key)` when token provided
- ✅ **Fallback**: Uses `HF_TOKEN` from environment if no token provided

**Implementation:**
```python
effective_hf_token = oauth_token or settings.hf_token or settings.huggingface_api_key
hf_provider = HuggingFaceProvider(api_key=effective_hf_token)
```

### 5. MCP Tools (`src/mcp_tools.py`)

#### Image OCR Tool
- ✅ **Token Support**: `extract_text_from_image()` accepts `hf_token` parameter
- ✅ **Token Fallback**: Uses `settings.hf_token` or `settings.huggingface_api_key` if not provided
- ✅ **Service Integration**: Passes token to `ImageOCRService.extract_text()`

#### Audio Transcription Tool
- ✅ **Token Support**: `transcribe_audio_file()` accepts `hf_token` parameter
- ✅ **Token Fallback**: Uses `settings.hf_token` or `settings.huggingface_api_key` if not provided
- ✅ **Service Integration**: Passes token to `STTService.transcribe_file()`

## Token Flow Diagram

```
User Login (OAuth)
    ↓
oauth_token.token
    ↓
app.py: token_value
    ↓
┌─────────────────────────────────────┐
│  Service Layer                       │
├─────────────────────────────────────┤
│  MultimodalService                   │
│    ↓ hf_token=token_value            │
│  AudioService                        │
│    ↓ hf_token=token_value            │
│  STTService / ImageOCRService        │
│    ↓ hf_token=token_value            │
│  Gradio Client(hf_token=token)       │
└─────────────────────────────────────┘

Alternative: Environment Variables
    ↓
HF_TOKEN or HUGGINGFACE_API_KEY
    ↓
settings.hf_token or settings.huggingface_api_key
    ↓
Same service flow as above
```

## Verification Checklist

- [x] STT Service accepts and uses `hf_token` parameter
- [x] Image OCR Service accepts and uses `hf_token` parameter
- [x] Audio Service passes token to STT service
- [x] Multimodal Service passes token to both audio and OCR services
- [x] App.py extracts OAuth token correctly
- [x] App.py passes token to multimodal service
- [x] HuggingFace API calls use token via `HuggingFaceProvider`
- [x] HuggingFace API calls use token via `InferenceClient`
- [x] MCP tools accept and use token parameter
- [x] Token priority is consistent: OAuth > Env Vars
- [x] Fallback to environment variables when OAuth not available

## Token Parameter Naming

All services consistently use `hf_token` parameter name:
- `STTService.transcribe_audio(..., hf_token=...)`
- `STTService.transcribe_file(..., hf_token=...)`
- `ImageOCRService.extract_text(..., hf_token=...)`
- `ImageOCRService.extract_text_from_image(..., hf_token=...)`
- `AudioService.process_audio_input(..., hf_token=...)`
- `MultimodalService.process_multimodal_input(..., hf_token=...)`
- `extract_text_from_image(..., hf_token=...)` (MCP tool)
- `transcribe_audio_file(..., hf_token=...)` (MCP tool)

## Gradio Client API Usage

According to Gradio documentation, the `Client` constructor accepts:
```python
Client(space_name, hf_token=None)
```

Our implementation correctly uses:
```python
Client(self.api_url, hf_token=token)  # When token available
Client(self.api_url)  # When no token (public Space)
```

## HuggingFace API Usage

### HuggingFaceProvider
```python
HuggingFaceProvider(api_key=effective_hf_token)
```
✅ Correctly passes token as `api_key` parameter

### InferenceClient
```python
InferenceClient(api_key=api_key)  # When token provided
InferenceClient()  # Falls back to HF_TOKEN env var
```
✅ Correctly passes token as `api_key` parameter

## Edge Cases Handled

1. **No Token Available**: Services work without token (public Gradio Spaces)
2. **Token Changes**: Client is recreated when token changes
3. **OAuth vs Env**: OAuth token takes priority over environment variables
4. **Multiple Token Sources**: Consistent priority across all services
5. **MCP Tools**: Support both explicit token and fallback to settings

## Recommendations

✅ **All implementations are correct and consistent**

The token authentication is properly implemented throughout:
- Gradio Client services accept and use tokens
- Service layer passes tokens through correctly
- Application layer extracts and passes OAuth tokens
- HuggingFace API calls use tokens via correct parameters
- MCP tools support token authentication
- Token priority is consistent across all layers

No changes needed - implementation follows best practices.

