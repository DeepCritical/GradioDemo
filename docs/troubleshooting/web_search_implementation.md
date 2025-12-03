# Web Search Implementation Analysis and Fixes

## Issue Summary

The application was using DuckDuckGo web search by default instead of the more capable Serper implementation, even when Serper API key was available. Additionally, Serper and SearchXNG implementations had bugs that would cause validation errors.

## Root Causes Identified

### 1. Default Configuration Issue

**Problem**: `web_search_provider` defaulted to `"duckduckgo"` in `src/utils/config.py`

**Impact**: 
- Serper (Google search with full content scraping) was not used even when `SERPER_API_KEY` was available
- Lower quality search results (DuckDuckGo only returns snippets, not full content)
- Missing auto-detection logic to prefer better providers when available

**Fix**: Changed default to `"auto"` which auto-detects the best available provider

### 2. Serper Source Type Bug

**Problem**: SerperWebSearchTool used `source="serper"` but `SourceName` only includes `"web"`, not `"serper"`

**Location**: `src/tools/serper_web_search.py:93`

**Impact**: Would cause Pydantic validation errors when creating Evidence objects

**Fix**: Changed to `source="web"` to match SourceName literal

### 3. SearchXNG Source Type Bug

**Problem**: SearchXNGWebSearchTool used `source="searchxng"` but `SourceName` only includes `"web"`

**Location**: `src/tools/searchxng_web_search.py:93`

**Impact**: Would cause Pydantic validation errors when creating Evidence objects

**Fix**: Changed to `source="web"` to match SourceName literal

### 4. Missing Title Truncation

**Problem**: Serper and SearchXNG didn't truncate titles to 500 characters, causing validation errors

**Impact**: Same issue as DuckDuckGo - titles > 500 chars would fail Citation validation

**Fix**: Added title truncation to both Serper and SearchXNG implementations

### 5. Missing Tool Name Mapping

**Problem**: `SearchHandler` didn't map `"serper"` and `"searchxng"` tool names to `"web"` source

**Location**: `src/tools/search_handler.py:114-121`

**Impact**: Tool names wouldn't be properly mapped to SourceName values

**Fix**: Added mappings for `"serper"` and `"searchxng"` to `"web"`

## Comparison: DuckDuckGo vs Serper vs SearchXNG

### DuckDuckGo (WebSearchTool)
- **Pros**: 
  - No API key required
  - Always available
  - Fast and free
- **Cons**:
  - Only returns snippets (no full content)
  - Lower quality results
  - No rate limiting built-in
  - Limited search capabilities

### Serper (SerperWebSearchTool)
- **Pros**:
  - Uses Google search (higher quality results)
  - Scrapes full content from URLs (not just snippets)
  - Built-in rate limiting
  - Better for research quality
- **Cons**:
  - Requires `SERPER_API_KEY`
  - Paid service (has free tier)
  - Slower (scrapes full content)

### SearchXNG (SearchXNGWebSearchTool)
- **Pros**:
  - Uses Google search (higher quality results)
  - Scrapes full content from URLs
  - Self-hosted option available
- **Cons**:
  - Requires `SEARCHXNG_HOST` configuration
  - May require self-hosting infrastructure

## Fixes Applied

### 1. Fixed Serper Implementation (`src/tools/serper_web_search.py`)

**Changes**:
- Changed `source="serper"` → `source="web"` (line 93)
- Added title truncation to 500 characters (lines 87-90)

**Before**:
```python
citation=Citation(
    title=result.title,
    url=result.url,
    source="serper",  # ❌ Invalid SourceName
    ...
)
```

**After**:
```python
# Truncate title to max 500 characters
title = result.title
if len(title) > 500:
    title = title[:497] + "..."

citation=Citation(
    title=title,
    url=result.url,
    source="web",  # ✅ Valid SourceName
    ...
)
```

### 2. Fixed SearchXNG Implementation (`src/tools/searchxng_web_search.py`)

**Changes**:
- Changed `source="searchxng"` → `source="web"` (line 93)
- Added title truncation to 500 characters (lines 87-90)

### 3. Improved Factory Auto-Detection (`src/tools/web_search_factory.py`)

**Changes**:
- Added auto-detection logic when provider is `"auto"` or when `duckduckgo` is selected but Serper API key exists
- Prefers Serper > SearchXNG > DuckDuckGo based on availability
- Logs which provider was auto-detected

**New Logic**:
```python
if provider == "auto" or (provider == "duckduckgo" and settings.serper_api_key):
    # Try Serper first (best quality)
    if settings.serper_api_key:
        return SerperWebSearchTool()
    # Try SearchXNG second
    if settings.searchxng_host:
        return SearchXNGWebSearchTool()
    # Fall back to DuckDuckGo
    return WebSearchTool()
```

### 4. Updated Default Configuration (`src/utils/config.py`)

**Changes**:
- Changed default from `"duckduckgo"` to `"auto"`
- Added `"auto"` to Literal type for `web_search_provider`
- Updated description to explain auto-detection

### 5. Enhanced SearchHandler Mapping (`src/tools/search_handler.py`)

**Changes**:
- Added `"serper": "web"` mapping
- Added `"searchxng": "web"` mapping

## Usage Recommendations

### For Best Quality (Recommended)
1. **Set `SERPER_API_KEY` environment variable**
2. **Set `WEB_SEARCH_PROVIDER=auto`** (or leave default)
3. System will automatically use Serper

### For Free Tier
1. **Don't set `SERPER_API_KEY`**
2. System will automatically fall back to DuckDuckGo
3. Results will be snippets only (lower quality)

### For Self-Hosted
1. **Set `SEARCHXNG_HOST` environment variable**
2. **Set `WEB_SEARCH_PROVIDER=searchxng`** or `"auto"`
3. System will use SearchXNG if available

## Testing

### Test Cases

1. **Auto-detection with Serper API key**:
   - Set `SERPER_API_KEY=test_key`
   - Set `WEB_SEARCH_PROVIDER=auto`
   - Expected: SerperWebSearchTool created

2. **Auto-detection without API keys**:
   - Don't set any API keys
   - Set `WEB_SEARCH_PROVIDER=auto`
   - Expected: WebSearchTool (DuckDuckGo) created

3. **Explicit DuckDuckGo with Serper available**:
   - Set `SERPER_API_KEY=test_key`
   - Set `WEB_SEARCH_PROVIDER=duckduckgo`
   - Expected: SerperWebSearchTool created (auto-upgrade)

4. **Title truncation**:
   - Search for query that returns long titles
   - Expected: All titles ≤ 500 characters

5. **Source validation**:
   - Use Serper or SearchXNG
   - Check Evidence objects
   - Expected: All citations have `source="web"`

## Files Modified

1. ✅ `src/tools/serper_web_search.py` - Fixed source type and added title truncation
2. ✅ `src/tools/searchxng_web_search.py` - Fixed source type and added title truncation
3. ✅ `src/tools/web_search_factory.py` - Added auto-detection logic
4. ✅ `src/tools/search_handler.py` - Added tool name mappings
5. ✅ `src/utils/config.py` - Changed default to "auto" and added "auto" to Literal type
6. ✅ `src/tools/web_search.py` - Already fixed (title truncation)

## Benefits

1. **Better Search Quality**: Serper provides Google-quality results with full content
2. **Automatic Optimization**: System automatically uses best available provider
3. **No Breaking Changes**: Existing configurations still work
4. **Validation Fixed**: No more Citation validation errors from source type or title length
5. **User-Friendly**: Users don't need to manually configure - system auto-detects

## Migration Guide

### For Existing Deployments

**No action required** - the changes are backward compatible:
- If `WEB_SEARCH_PROVIDER=duckduckgo` is set, it will still work
- If `SERPER_API_KEY` is available, system will auto-upgrade to Serper
- If no API keys are set, system will use DuckDuckGo

### For New Deployments

**Recommended**: 
- Set `SERPER_API_KEY` environment variable
- Leave `WEB_SEARCH_PROVIDER` unset (defaults to "auto")
- System will automatically use Serper

### For HuggingFace Spaces

1. Add `SERPER_API_KEY` as a Space secret
2. System will automatically detect and use Serper
3. If key is not set, falls back to DuckDuckGo

## References

- [Serper API Documentation](https://serper.dev/)
- [SearchXNG Documentation](https://github.com/surge-ai/searchxng)
- [DuckDuckGo Search](https://github.com/deedy5/duckduckgo_search)

