# OAuth Investigation: Gradio and Hugging Face Hub

## Overview

This document provides a comprehensive investigation of OAuth authentication features available in Gradio and Hugging Face Hub, and how they can be used in the DeepCritical application.

## 1. Gradio OAuth Features

### 1.1 Enabling OAuth in Gradio

**For Hugging Face Spaces:**
- OAuth is automatically enabled when your Space is hosted on Hugging Face
- Add the following metadata to your `README.md` to register your Space as an OAuth application:
  ```yaml
  ---
  hf_oauth: true
  hf_oauth_expiration_minutes: 480  # Token expiration time (8 hours)
  hf_oauth_scopes:
    - inference-api  # Required for Inference API access
    # - read-billing  # Optional: for billing information
  ---
  ```
- This configuration registers your Space as an OAuth application on Hugging Face automatically
- **Current DeepCritical Configuration** (from `README.md`):
  - `hf_oauth: true` ✅ Enabled
  - `hf_oauth_expiration_minutes: 480` (8 hours)
  - `hf_oauth_scopes: [inference-api]` ✅ Required scope configured

**For Local Development:**
- OAuth requires a Hugging Face OAuth application to be created manually
- You need to configure redirect URIs and scopes in your Hugging Face account settings

### 1.2 Gradio OAuth Components

#### `gr.LoginButton`
- **Purpose**: Displays a "Sign in with Hugging Face" button
- **Usage**:
  ```python
  login_button = gr.LoginButton("Sign in with Hugging Face")
  ```
- **Behavior**:
  - When clicked, redirects user to Hugging Face OAuth authorization page
  - After authorization, user is redirected back to the application
  - The OAuth token and profile are automatically available in function parameters

#### `gr.OAuthToken`
- **Purpose**: Contains the OAuth access token
- **Attributes**:
  - `.token`: The access token string (used for API authentication)
- **Availability**:
  - Automatically passed as a function parameter when OAuth is enabled
  - `None` if user is not logged in
- **Usage**:
  ```python
  def my_function(oauth_token: gr.OAuthToken | None = None):
      if oauth_token is not None:
          token_value = oauth_token.token
          # Use token_value for API calls
  ```

#### `gr.OAuthProfile`
- **Purpose**: Contains user profile information
- **Attributes**:
  - `.username`: User's Hugging Face username
  - `.name`: User's display name
  - `.profile_image`: URL to user's profile image
- **Availability**:
  - Automatically passed as a function parameter when OAuth is enabled
  - `None` if user is not logged in
- **Usage**:
  ```python
  def my_function(oauth_profile: gr.OAuthProfile | None = None):
      if oauth_profile is not None:
          username = oauth_profile.username
          name = oauth_profile.name
  ```

### 1.3 Automatic Parameter Injection

**Key Feature**: Gradio automatically injects `gr.OAuthToken` and `gr.OAuthProfile` as function parameters when:
- OAuth is enabled (via `hf_oauth: true` in README.md for Spaces)
- The function signature includes these parameters
- User is logged in

**Example**:
```python
async def research_agent(
    message: str,
    oauth_token: gr.OAuthToken | None = None,
    oauth_profile: gr.OAuthProfile | None = None,
):
    # oauth_token and oauth_profile are automatically provided
    # They are None if user is not logged in
    if oauth_token is not None:
        token = oauth_token.token
        # Use token for API calls
```

### 1.4 Limitations

- **No Direct Change Events**: Gradio doesn't support watching `OAuthToken`/`OAuthProfile` changes directly
- **Workaround**: Use a refresh button that users can click after logging in
- **Context Availability**: OAuth components are available in Gradio function context, but not as regular components that can be watched

## 2. Hugging Face Hub OAuth

### 2.1 OAuth Scopes

Hugging Face Hub supports various OAuth scopes that grant different permissions:

#### Available Scopes

1. **`openid`**
   - Basic OpenID Connect authentication
   - Required for OAuth login

2. **`profile`**
   - Access to user profile information (username, name, profile image)
   - Automatically included with `openid`

3. **`email`**
   - Access to user's email address
   - Optional, requires explicit request

4. **`read-repos`**
   - Read access to user's repositories
   - Allows listing and reading model/dataset repositories

5. **`write-repos`**
   - Write access to user's repositories
   - Allows creating, updating, and deleting repositories

6. **`inference-api`** ⭐ **CRITICAL FOR DEEPCRITICAL**
   - Access to Hugging Face Inference API
   - **This scope is required for using the Inference API**
   - Grants access to:
     - HuggingFace's own Inference API
     - All third-party inference providers (nebius, together, scaleway, hyperbolic, novita, nscale, sambanova, ovh, fireworks, etc.)
     - All models available through the Inference Providers API
   - **Reference**: https://huggingface.co/docs/hub/oauth#currently-supported-scopes

### 2.2 OAuth Application Configuration

**For Hugging Face Spaces:**
- OAuth application is automatically created when `hf_oauth: true` is set in README.md
- Scopes are automatically requested based on Space requirements
- Redirect URI is automatically configured

**For Manual OAuth Applications:**
1. Navigate to: https://huggingface.co/settings/applications
2. Click "New OAuth Application"
3. Fill in:
   - Application name
   - Homepage URL
   - Description
   - Authorization callback URL (redirect URI)
4. Select required scopes:
   - **For DeepCritical**: Must include `inference-api` scope
   - Also include: `openid`, `profile` (for user info)
5. Save and note the Client ID and Client Secret

### 2.3 OAuth Token Usage

#### Token Format
- OAuth tokens are Bearer tokens
- Format: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Valid until revoked or expired

#### Using OAuth Token for API Calls

**With `huggingface_hub` library:**
```python
from huggingface_hub import HfApi, InferenceClient

# Initialize API client with token
api = HfApi(token=oauth_token.token)

# Initialize Inference client with token
client = InferenceClient(
    model="meta-llama/Llama-3.1-8B-Instruct",
    api_key=oauth_token.token,
)
```

**With `pydantic-ai`:**
```python
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.huggingface import HuggingFaceProvider

# Create provider with OAuth token
provider = HuggingFaceProvider(api_key=oauth_token.token)
model = HuggingFaceModel("meta-llama/Llama-3.1-8B-Instruct", provider=provider)
```

**With HTTP requests:**
```python
import httpx

headers = {"Authorization": f"Bearer {oauth_token.token}"}
response = httpx.get("https://api-inference.huggingface.co/models", headers=headers)
```

### 2.4 Token Validation

**Check token validity:**
```python
from huggingface_hub import HfApi

api = HfApi(token=token)
user_info = api.whoami()  # Returns user info if token is valid
```

**Check token scopes:**
- Token scopes are determined at OAuth authorization time
- There's no direct API to query token scopes
- If API calls fail with 403, the token likely lacks required scopes
- For `inference-api` scope: Try making an inference API call to verify

## 3. Current Implementation in DeepCritical

### 3.1 OAuth Token Extraction

**Location**: `src/app.py` - `research_agent()` function

**Pattern**:
```python
if oauth_token is not None:
    if hasattr(oauth_token, "token"):
        token_value = oauth_token.token
    elif isinstance(oauth_token, str):
        token_value = oauth_token
```

### 3.2 OAuth Profile Extraction

**Location**: `src/app.py` - `research_agent()` function

**Pattern**:
```python
if oauth_profile is not None:
    username = (
        oauth_profile.username
        if hasattr(oauth_profile, "username") and oauth_profile.username
        else (
            oauth_profile.name
            if hasattr(oauth_profile, "name") and oauth_profile.name
            else None
        )
    )
```

### 3.3 Token Priority

**Current Priority Order**:
1. OAuth token (from `gr.OAuthToken`) - **Highest Priority**
2. `HF_TOKEN` environment variable
3. `HUGGINGFACE_API_KEY` environment variable

**Implementation**:
```python
effective_api_key = (
    oauth_token.token if oauth_token else
    os.getenv("HF_TOKEN") or
    os.getenv("HUGGINGFACE_API_KEY")
)
```

### 3.4 Model/Provider Validator

**Location**: `src/utils/hf_model_validator.py`

**Features**:
- `validate_oauth_token()`: Validates token and checks for `inference-api` scope
- `get_available_models()`: Queries HuggingFace Hub for available models
- `get_available_providers()`: Gets list of available inference providers
- `get_models_for_provider()`: Gets models available for a specific provider

**Usage in Interface**:
- Refresh button triggers `update_model_provider_dropdowns()`
- Function queries HuggingFace API using OAuth token
- Updates model and provider dropdowns dynamically

## 4. Best Practices

### 4.1 Token Security

- **Never log tokens**: Tokens are sensitive credentials
- **Never expose in client-side code**: Keep tokens server-side only
- **Validate before use**: Check token format and validity
- **Handle expiration**: Implement token refresh if needed

### 4.2 Scope Management

- **Request minimal scopes**: Only request scopes you actually need
- **Document scope requirements**: Clearly document which scopes are needed
- **Handle missing scopes gracefully**: Provide clear error messages if scopes are missing

### 4.3 Error Handling

- **403 Forbidden**: Usually means missing or invalid token, or missing scope
- **401 Unauthorized**: Token is invalid or expired
- **422 Unprocessable Entity**: Request format issue or model/provider incompatibility

### 4.4 User Experience

- **Clear authentication prompts**: Tell users why authentication is needed
- **Status indicators**: Show authentication status clearly
- **Helpful error messages**: Guide users to fix authentication issues
- **Refresh mechanisms**: Provide ways to refresh token or re-authenticate

## 5. Troubleshooting

### 5.1 Token Not Available

**Symptoms**: `oauth_token` is `None` in function

**Solutions**:
- Check if user is logged in (OAuth button clicked)
- Verify `hf_oauth: true` is in README.md (for Spaces)
- Check if OAuth is properly configured

### 5.2 403 Forbidden Errors

**Symptoms**: API calls fail with 403

**Solutions**:
- Verify token has `inference-api` scope
- Check token is being extracted correctly (`oauth_token.token`)
- Verify token is not expired
- Check if model requires special permissions

### 5.3 Models/Providers Not Loading

**Symptoms**: Dropdowns don't update after login

**Solutions**:
- Click "Refresh Available Models" button after logging in
- Check token has `inference-api` scope
- Verify API calls are succeeding (check logs)
- Check network connectivity

## 6. References

- **Gradio OAuth Docs**: https://www.gradio.app/docs/gradio/loginbutton
- **Hugging Face OAuth Docs**: https://huggingface.co/docs/hub/en/oauth
- **Hugging Face OAuth Scopes**: https://huggingface.co/docs/hub/oauth#currently-supported-scopes
- **Hugging Face Inference API**: https://huggingface.co/docs/api-inference/index
- **Hugging Face Inference Providers**: https://huggingface.co/docs/inference-providers/index

## 7. Future Enhancements

### 7.1 Automatic Dropdown Updates

**Current Limitation**: Dropdowns don't update automatically when user logs in

**Potential Solutions**:
- Use Gradio's `load` event on components
- Implement polling mechanism to check authentication status
- Use JavaScript callbacks (if Gradio supports)

### 7.2 Scope Validation

**Current**: Scope validation is implicit (via API call failures)

**Potential Enhancement**:
- Query token metadata to verify scopes explicitly
- Display available scopes in UI
- Warn users if required scopes are missing

### 7.3 Token Refresh

**Current**: Tokens are used until they expire

**Potential Enhancement**:
- Implement token refresh mechanism
- Handle token expiration gracefully
- Prompt user to re-authenticate when token expires

