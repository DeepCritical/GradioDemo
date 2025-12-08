# SERPER API 403 Forbidden Error - Troubleshooting Guide

## What is the Error?

The error you're seeing is:
```
error="403, message='Forbidden', url='https://google.serper.dev/search'"
Serper API request failed: 403, message='Forbidden'
```

A **403 Forbidden** HTTP status code from the Serper API means your request was rejected due to authentication/authorization issues.

## Root Causes

### 1. **Invalid or Missing API Key** (Most Common)
- The `SERPER_API_KEY` environment variable is either:
  - Not set
  - Set to an invalid/expired key
  - Contains extra whitespace or formatting issues
  - Typo in the key value

### 2. **API Key Permissions**
- The API key doesn't have permission to access the Serper API
- The key might be for a different Serper service/endpoint

### 3. **Account/Billing Issues**
- Your Serper account might be:
  - Suspended
  - Over quota/limit
  - Has billing issues (payment failed)
  - Account expired

### 4. **API Key Format Issues**
- The key might be malformed
- Missing characters
- Wrong key type (e.g., using a test key in production)

## How to Diagnose

### Step 1: Verify API Key is Set

Check if the environment variable is set:

**Linux/Mac:**
```bash
echo $SERPER_API_KEY
```

**Windows (PowerShell):**
```powershell
$env:SERPER_API_KEY
```

**Windows (CMD):**
```cmd
echo %SERPER_API_KEY%
```

### Step 2: Test the API Key Directly

Test your Serper API key using curl:

```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"q": "test query"}'
```

If you get a 403, the key is invalid. If you get 200, the key works.

### Step 3: Check Serper Dashboard

1. Go to [Serper.dev Dashboard](https://serper.dev/dashboard)
2. Log in to your account
3. Check:
   - API key status
   - Usage/quota limits
   - Billing status
   - Account status

## Solutions

### Solution 1: Get a Valid Serper API Key

1. **Sign up for Serper:**
   - Visit [serper.dev](https://serper.dev)
   - Create an account or log in

2. **Get your API key:**
   - Go to Dashboard → API Keys
   - Copy your API key

3. **Set the environment variable:**

   **Linux/Mac:**
   ```bash
   export SERPER_API_KEY="your_api_key_here"
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:SERPER_API_KEY = "your_api_key_here"
   ```

   **Windows (CMD):**
   ```cmd
   set SERPER_API_KEY=your_api_key_here
   ```

   **For Hugging Face Spaces:**
   - Go to your Space settings
   - Add `SERPER_API_KEY` as a secret/environment variable

4. **Verify it's set correctly:**
   ```bash
   # Check for whitespace issues
   echo "|$SERPER_API_KEY|"  # Should show key between pipes with no extra spaces
   ```

### Solution 2: Use a Different Search Provider (Temporary Fix)

If you can't fix the Serper API key immediately, switch to DuckDuckGo (free, no API key required):

**Set environment variable:**
```bash
export WEB_SEARCH_PROVIDER="duckduckgo"
```

Or in your `.env` file:
```env
WEB_SEARCH_PROVIDER=duckduckgo
```

**Note:** DuckDuckGo provides lower quality results (snippets only, no full content scraping) but will work without an API key.

### Solution 3: Check Account Status

1. Log into [Serper Dashboard](https://serper.dev/dashboard)
2. Verify:
   - Account is active
   - No billing issues
   - Quota not exceeded
   - API key is not revoked

### Solution 4: Regenerate API Key

If your key might be compromised or invalid:

1. Go to Serper Dashboard
2. Revoke the old key
3. Generate a new API key
4. Update your environment variable

## Code Improvements (Optional)

The current code doesn't handle 403 errors specifically. Here's what could be improved:

### Current Behavior
- 403 errors are treated as generic `SearchError`
- System retries 3 times (wasteful - 403 won't fix itself)
- No automatic fallback to other providers

### Recommended Improvements

1. **Detect 403 specifically** and treat as configuration error (not transient)
2. **Disable Serper** after 403 and fall back to DuckDuckGo
3. **Log clearer error messages** with troubleshooting hints

## Quick Fix for Your Current Issue

**Immediate workaround:**

1. **Remove or comment out SERPER_API_KEY:**
   ```bash
   unset SERPER_API_KEY
   ```

2. **Set provider to DuckDuckGo:**
   ```bash
   export WEB_SEARCH_PROVIDER="duckduckgo"
   ```

3. **Restart your application**

This will use DuckDuckGo instead of Serper, allowing your research to continue (though with lower quality results).

## Prevention

1. **Validate API keys at startup** - Check if key works before using it
2. **Use environment variable validation** - Ensure key format is correct
3. **Monitor API usage** - Set up alerts for quota limits
4. **Have fallback providers** - Always have DuckDuckGo as backup

## Summary

- **403 Forbidden** = Invalid/missing API key or account issues
- **Fix:** Get valid Serper API key from [serper.dev](https://serper.dev)
- **Workaround:** Use `WEB_SEARCH_PROVIDER=duckduckgo` for free search
- **Test:** Use curl to verify your API key works
- **Check:** Serper dashboard for account/billing status



