# OAuth Summary: Quick Reference

## Current Configuration

**Status**: ✅ OAuth is properly configured in DeepCritical

**Configuration** (from `README.md`):
```yaml
hf_oauth: true
hf_oauth_expiration_minutes: 480
hf_oauth_scopes:
  - inference-api
```

## Key OAuth Components

### 1. Gradio Components

| Component | Purpose | Usage |
|-----------|---------|-------|
| `gr.LoginButton` | Display login button | `gr.LoginButton("Sign in with Hugging Face")` |
| `gr.OAuthToken` | Access token | `oauth_token.token` (string) |
| `gr.OAuthProfile` | User profile | `oauth_profile.username`, `oauth_profile.name` |

### 2. OAuth Scopes

| Scope | Required | Purpose |
|-------|----------|---------|
| `inference-api` | ✅ **YES** | Access to HuggingFace Inference API and all providers |
| `openid` | ✅ Auto | Basic authentication |
| `profile` | ✅ Auto | User profile information |
| `read-billing` | ❌ Optional | Billing information access |

## Token Usage Pattern

```python
# Extract token
if oauth_token is not None:
    token_value = oauth_token.token  # Get token string
    
# Use token for API calls
effective_api_key = (
    oauth_token.token if oauth_token else
    os.getenv("HF_TOKEN") or
    os.getenv("HUGGINGFACE_API_KEY")
)
```

## Available OAuth Features

### ✅ Implemented

1. **OAuth Login Button** - Users can sign in with Hugging Face
2. **Token Extraction** - OAuth token is extracted and used for API calls
3. **Profile Access** - Username and profile info are available
4. **Model/Provider Validator** - Queries available models using OAuth token
5. **Token Priority** - OAuth token takes priority over env vars

### ⚠️ Limitations

1. **No Auto-Update** - Dropdowns don't update automatically when user logs in
   - **Workaround**: "Refresh Available Models" button
2. **No Scope Validation** - Can't directly query token scopes
   - **Workaround**: Try API call, check for 403 errors
3. **No Token Refresh** - Tokens expire after 8 hours
   - **Workaround**: User must re-authenticate

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `oauth_token` is `None` | User must click login button first |
| 403 Forbidden errors | Check if token has `inference-api` scope |
| Models not loading | Click "Refresh Available Models" button |
| Token expired | User must re-authenticate (login again) |

## Quick Reference Links

- **Full Investigation**: See `oauth_investigation.md`
- **Gradio OAuth Docs**: https://www.gradio.app/docs/gradio/loginbutton
- **HF OAuth Docs**: https://huggingface.co/docs/hub/en/oauth
- **HF OAuth Scopes**: https://huggingface.co/docs/hub/oauth#currently-supported-scopes

