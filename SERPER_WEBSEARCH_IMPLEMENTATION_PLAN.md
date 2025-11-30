# SERPER Web Search Implementation Plan

## Executive Summary

This plan details the implementation of SERPER-based web search by vendoring code from `folder/tools/web_search.py` into `src/tools/`, creating a protocol-compliant `SerperWebSearchTool`, fixing the existing `WebSearchTool`, and integrating both into the main search flow.

## Project Structure

### Project 1: Vendor and Refactor Core Web Search Components
**Goal**: Extract and vendor Serper/SearchXNG search logic from `folder/tools/web_search.py` into `src/tools/`

### Project 2: Create Protocol-Compliant SerperWebSearchTool
**Goal**: Implement `SerperWebSearchTool` class that fully complies with `SearchTool` protocol

### Project 3: Fix Existing WebSearchTool Protocol Compliance
**Goal**: Make existing `WebSearchTool` (DuckDuckGo) protocol-compliant

### Project 4: Integrate Web Search into SearchHandler
**Goal**: Add web search tools to main search flow in `src/app.py`

### Project 5: Update Callers and Dependencies
**Goal**: Update all code that uses web search to work with new implementation

### Project 6: Testing and Validation
**Goal**: Add comprehensive tests for all web search implementations

---

## Detailed Implementation Plan

### PROJECT 1: Vendor and Refactor Core Web Search Components

#### Activity 1.1: Create Vendor Module Structure
**File**: `src/tools/vendored/__init__.py`
- **Task 1.1.1**: Create `src/tools/vendored/` directory
- **Task 1.1.2**: Create `__init__.py` with exports

**File**: `src/tools/vendored/web_search_core.py`
- **Task 1.1.3**: Vendor `ScrapeResult`, `WebpageSnippet`, `SearchResults` models from `folder/tools/web_search.py` (lines 23-37)
- **Task 1.1.4**: Vendor `scrape_urls()` function (lines 274-299)
- **Task 1.1.5**: Vendor `fetch_and_process_url()` function (lines 302-348)
- **Task 1.1.6**: Vendor `html_to_text()` function (lines 351-368)
- **Task 1.1.7**: Vendor `is_valid_url()` function (lines 371-410)
- **Task 1.1.8**: Vendor `ssl_context` setup (lines 115-120)
- **Task 1.1.9**: Add imports: `aiohttp`, `asyncio`, `BeautifulSoup`, `ssl`
- **Task 1.1.10**: Add `CONTENT_LENGTH_LIMIT = 10000` constant
- **Task 1.1.11**: Add type hints following project standards
- **Task 1.1.12**: Add structlog logging
- **Task 1.1.13**: Replace `print()` statements with `logger` calls

**File**: `src/tools/vendored/serper_client.py`
- **Task 1.1.14**: Vendor `SerperClient` class from `folder/tools/web_search.py` (lines 123-196)
- **Task 1.1.15**: Remove dependency on `ResearchAgent` and `ResearchRunner`
- **Task 1.1.16**: Replace filter agent with simple relevance filtering or remove it
- **Task 1.1.17**: Add `__init__` that takes `api_key: str | None` parameter
- **Task 1.1.18**: Update `search()` method to return `list[WebpageSnippet]` without filtering
- **Task 1.1.19**: Remove `_filter_results()` method (or make it optional)
- **Task 1.1.20**: Add error handling with `SearchError` and `RateLimitError`
- **Task 1.1.21**: Add structlog logging
- **Task 1.1.22**: Add type hints

**File**: `src/tools/vendored/searchxng_client.py`
- **Task 1.1.23**: Vendor `SearchXNGClient` class from `folder/tools/web_search.py` (lines 199-271)
- **Task 1.1.24**: Remove dependency on `ResearchAgent` and `ResearchRunner`
- **Task 1.1.25**: Replace filter agent with simple relevance filtering or remove it
- **Task 1.1.26**: Add `__init__` that takes `host: str` parameter
- **Task 1.1.27**: Update `search()` method to return `list[WebpageSnippet]` without filtering
- **Task 1.1.28**: Remove `_filter_results()` method (or make it optional)
- **Task 1.1.29**: Add error handling with `SearchError` and `RateLimitError`
- **Task 1.1.30**: Add structlog logging
- **Task 1.1.31**: Add type hints

#### Activity 1.2: Create Rate Limiting for Web Search
**File**: `src/tools/rate_limiter.py`
- **Task 1.2.1**: Add `get_serper_limiter()` function (rate: "10/second" with API key)
- **Task 1.2.2**: Add `get_searchxng_limiter()` function (rate: "5/second")
- **Task 1.2.3**: Use `RateLimiterFactory.get()` pattern

---

### PROJECT 2: Create Protocol-Compliant SerperWebSearchTool

#### Activity 2.1: Implement SerperWebSearchTool Class
**File**: `src/tools/serper_web_search.py`
- **Task 2.1.1**: Create new file `src/tools/serper_web_search.py`
- **Task 2.1.2**: Add imports:
  - `from src.tools.base import SearchTool`
  - `from src.tools.vendored.serper_client import SerperClient`
  - `from src.tools.vendored.web_search_core import scrape_urls, WebpageSnippet`
  - `from src.tools.rate_limiter import get_serper_limiter`
  - `from src.tools.query_utils import preprocess_query`
  - `from src.utils.config import settings`
  - `from src.utils.exceptions import SearchError, RateLimitError`
  - `from src.utils.models import Citation, Evidence`
  - `import structlog`
  - `from tenacity import retry, stop_after_attempt, wait_exponential`

- **Task 2.1.3**: Create `SerperWebSearchTool` class
- **Task 2.1.4**: Add `__init__(self, api_key: str | None = None)` method
  - Line 2.1.4.1: Get API key from parameter or `settings.serper_api_key`
  - Line 2.1.4.2: Validate API key is not None, raise `ConfigurationError` if missing
  - Line 2.1.4.3: Initialize `SerperClient(api_key=self.api_key)`
  - Line 2.1.4.4: Get rate limiter: `self._limiter = get_serper_limiter(self.api_key)`

- **Task 2.1.5**: Add `@property def name(self) -> str:` returning `"serper"`

- **Task 2.1.6**: Add `async def _rate_limit(self) -> None:` method
  - Line 2.1.6.1: Call `await self._limiter.acquire()`

- **Task 2.1.7**: Add `@retry(...)` decorator with exponential backoff

- **Task 2.1.8**: Add `async def search(self, query: str, max_results: int = 10) -> list[Evidence]:` method
  - Line 2.1.8.1: Call `await self._rate_limit()`
  - Line 2.1.8.2: Preprocess query: `clean_query = preprocess_query(query)`
  - Line 2.1.8.3: Use `clean_query if clean_query else query`
  - Line 2.1.8.4: Call `search_results = await self._client.search(query, filter_for_relevance=False, max_results=max_results)`
  - Line 2.1.8.5: Call `scraped = await scrape_urls(search_results)`
  - Line 2.1.8.6: Convert `ScrapeResult` to `Evidence` objects:
    - Line 2.1.8.6.1: Create `Citation` with `title`, `url`, `source="serper"`, `date="Unknown"`, `authors=[]`
    - Line 2.1.8.6.2: Create `Evidence` with `content=scraped.text`, `citation`, `relevance=0.0`
  - Line 2.1.8.7: Return `list[Evidence]`
  - Line 2.1.8.8: Add try/except for `httpx.HTTPStatusError`:
    - Line 2.1.8.8.1: Check for 429 status, raise `RateLimitError`
    - Line 2.1.8.8.2: Otherwise raise `SearchError`
  - Line 2.1.8.9: Add try/except for `httpx.TimeoutException`, raise `SearchError`
  - Line 2.1.8.10: Add generic exception handler, log and raise `SearchError`

#### Activity 2.2: Implement SearchXNGWebSearchTool Class
**File**: `src/tools/searchxng_web_search.py`
- **Task 2.2.1**: Create new file `src/tools/searchxng_web_search.py`
- **Task 2.2.2**: Add imports (similar to SerperWebSearchTool)
- **Task 2.2.3**: Create `SearchXNGWebSearchTool` class
- **Task 2.2.4**: Add `__init__(self, host: str | None = None)` method
  - Line 2.2.4.1: Get host from parameter or `settings.searchxng_host`
  - Line 2.2.4.2: Validate host is not None, raise `ConfigurationError` if missing
  - Line 2.2.4.3: Initialize `SearchXNGClient(host=self.host)`
  - Line 2.2.4.4: Get rate limiter: `self._limiter = get_searchxng_limiter()`

- **Task 2.2.5**: Add `@property def name(self) -> str:` returning `"searchxng"`

- **Task 2.2.6**: Add `async def _rate_limit(self) -> None:` method

- **Task 2.2.7**: Add `@retry(...)` decorator

- **Task 2.2.8**: Add `async def search(self, query: str, max_results: int = 10) -> list[Evidence]:` method
  - Line 2.2.8.1-2.2.8.10: Similar structure to SerperWebSearchTool

---

### PROJECT 3: Fix Existing WebSearchTool Protocol Compliance

#### Activity 3.1: Update WebSearchTool Class
**File**: `src/tools/web_search.py`
- **Task 3.1.1**: Add `@property def name(self) -> str:` method returning `"duckduckgo"` (after line 17)

- **Task 3.1.2**: Change `search()` return type from `SearchResult` to `list[Evidence]` (line 19)

- **Task 3.1.3**: Update `search()` method body:
  - Line 3.1.3.1: Keep existing search logic (lines 21-43)
  - Line 3.1.3.2: Instead of returning `SearchResult`, return `evidence` list directly (line 44)
  - Line 3.1.3.3: Update exception handler to return empty list `[]` instead of `SearchResult` (line 51)

- **Task 3.1.4**: Add imports if needed:
  - Line 3.1.4.1: `from src.utils.exceptions import SearchError`
  - Line 3.1.4.2: Update exception handling to raise `SearchError` instead of returning error `SearchResult`

- **Task 3.1.5**: Add query preprocessing:
  - Line 3.1.5.1: Import `from src.tools.query_utils import preprocess_query`
  - Line 3.1.5.2: Add `clean_query = preprocess_query(query)` before search
  - Line 3.1.5.3: Use `clean_query if clean_query else query`

#### Activity 3.2: Update Retrieval Agent Caller
**File**: `src/agents/retrieval_agent.py`
- **Task 3.2.1**: Update `search_web()` function (line 31):
  - Line 3.2.1.1: Change `results = await _web_search.search(query, max_results)` 
  - Line 3.2.1.2: Change to `evidence = await _web_search.search(query, max_results)`
  - Line 3.2.1.3: Update check: `if not evidence:` instead of `if not results.evidence:`
  - Line 3.2.1.4: Update state update: `new_count = state.add_evidence(evidence)` instead of `results.evidence`
  - Line 3.2.1.5: Update logging: `results_found=len(evidence)` instead of `len(results.evidence)`
  - Line 3.2.1.6: Update output formatting: `for i, r in enumerate(evidence[:max_results], 1):` instead of `results.evidence[:max_results]`
  - Line 3.2.1.7: Update deduplication: `await state.embedding_service.deduplicate(evidence)` instead of `results.evidence`
  - Line 3.2.1.8: Update output message: `Found {len(evidence)} web results` instead of `len(results.evidence)`

---

### PROJECT 4: Integrate Web Search into SearchHandler

#### Activity 4.1: Create Web Search Tool Factory
**File**: `src/tools/web_search_factory.py`
- **Task 4.1.1**: Create new file `src/tools/web_search_factory.py`
- **Task 4.1.2**: Add imports:
  - `from src.tools.web_search import WebSearchTool`
  - `from src.tools.serper_web_search import SerperWebSearchTool`
  - `from src.tools.searchxng_web_search import SearchXNGWebSearchTool`
  - `from src.utils.config import settings`
  - `from src.utils.exceptions import ConfigurationError`
  - `import structlog`

- **Task 4.1.3**: Add `logger = structlog.get_logger()`

- **Task 4.1.4**: Create `def create_web_search_tool() -> SearchTool | None:` function
  - Line 4.1.4.1: Check `settings.web_search_provider`
  - Line 4.1.4.2: If `"serper"`:
    - Line 4.1.4.2.1: Check `settings.serper_api_key` or `settings.web_search_available()`
    - Line 4.1.4.2.2: If available, return `SerperWebSearchTool()`
    - Line 4.1.4.2.3: Else log warning and return `None`
  - Line 4.1.4.3: If `"searchxng"`:
    - Line 4.1.4.3.1: Check `settings.searchxng_host` or `settings.web_search_available()`
    - Line 4.1.4.3.2: If available, return `SearchXNGWebSearchTool()`
    - Line 4.1.4.3.3: Else log warning and return `None`
  - Line 4.1.4.4: If `"duckduckgo"`:
    - Line 4.1.4.4.1: Return `WebSearchTool()` (always available)
  - Line 4.1.4.5: If `"brave"` or `"tavily"`:
    - Line 4.1.4.5.1: Log warning "Not yet implemented"
    - Line 4.1.4.5.2: Return `None`
  - Line 4.1.4.6: Default: return `WebSearchTool()` (fallback to DuckDuckGo)

#### Activity 4.2: Update SearchHandler Initialization
**File**: `src/app.py`
- **Task 4.2.1**: Add import: `from src.tools.web_search_factory import create_web_search_tool`

- **Task 4.2.2**: Update `configure_orchestrator()` function (around line 73):
  - Line 4.2.2.1: Before creating `SearchHandler`, call `web_search_tool = create_web_search_tool()`
  - Line 4.2.2.2: Create tools list: `tools = [PubMedTool(), ClinicalTrialsTool(), EuropePMCTool()]`
  - Line 4.2.2.3: If `web_search_tool is not None`:
    - Line 4.2.2.3.1: Append `web_search_tool` to tools list
    - Line 4.2.2.3.2: Log info: "Web search tool added to search handler"
  - Line 4.2.2.4: Update `SearchHandler` initialization to use `tools` list

---

### PROJECT 5: Update Callers and Dependencies

#### Activity 5.1: Update web_search_adapter
**File**: `src/tools/web_search_adapter.py`
- **Task 5.1.1**: Update `web_search()` function to use new implementation:
  - Line 5.1.1.1: Import `from src.tools.web_search_factory import create_web_search_tool`
  - Line 5.1.1.2: Remove dependency on `folder.tools.web_search`
  - Line 5.1.1.3: Get tool: `tool = create_web_search_tool()`
  - Line 5.1.1.4: If `tool is None`, return error message
  - Line 5.1.1.5: Call `evidence = await tool.search(query, max_results=5)`
  - Line 5.1.1.6: Convert `Evidence` objects to formatted string:
    - Line 5.1.1.6.1: Format each evidence with title, URL, content preview
  - Line 5.1.1.7: Return formatted string

#### Activity 5.2: Update Tool Executor
**File**: `src/tools/tool_executor.py`
- **Task 5.2.1**: Verify `web_search_adapter.web_search()` usage (line 86) still works
- **Task 5.2.2**: No changes needed if adapter is updated correctly

#### Activity 5.3: Update Planner Agent
**File**: `src/orchestrator/planner_agent.py`
- **Task 5.3.1**: Verify `web_search_adapter.web_search()` usage (line 14) still works
- **Task 5.3.2**: No changes needed if adapter is updated correctly

#### Activity 5.4: Remove Legacy Dependencies
**File**: `src/tools/web_search_adapter.py`
- **Task 5.4.1**: Remove import of `folder.llm_config` and `folder.tools.web_search`
- **Task 5.4.2**: Update error messages to reflect new implementation

---

### PROJECT 6: Testing and Validation

#### Activity 6.1: Unit Tests for Vendored Components
**File**: `tests/unit/tools/test_vendored_web_search_core.py`
- **Task 6.1.1**: Test `scrape_urls()` function
- **Task 6.1.2**: Test `fetch_and_process_url()` function
- **Task 6.1.3**: Test `html_to_text()` function
- **Task 6.1.4**: Test `is_valid_url()` function

**File**: `tests/unit/tools/test_vendored_serper_client.py`
- **Task 6.1.5**: Mock SerperClient API calls
- **Task 6.1.6**: Test successful search
- **Task 6.1.7**: Test error handling
- **Task 6.1.8**: Test rate limiting

**File**: `tests/unit/tools/test_vendored_searchxng_client.py`
- **Task 6.1.9**: Mock SearchXNGClient API calls
- **Task 6.1.10**: Test successful search
- **Task 6.1.11**: Test error handling
- **Task 6.1.12**: Test rate limiting

#### Activity 6.2: Unit Tests for Web Search Tools
**File**: `tests/unit/tools/test_serper_web_search.py`
- **Task 6.2.1**: Test `SerperWebSearchTool.__init__()` with valid API key
- **Task 6.2.2**: Test `SerperWebSearchTool.__init__()` without API key (should raise)
- **Task 6.2.3**: Test `name` property returns `"serper"`
- **Task 6.2.4**: Test `search()` returns `list[Evidence]`
- **Task 6.2.5**: Test `search()` with mocked SerperClient
- **Task 6.2.6**: Test error handling (SearchError, RateLimitError)
- **Task 6.2.7**: Test query preprocessing
- **Task 6.2.8**: Test rate limiting

**File**: `tests/unit/tools/test_searchxng_web_search.py`
- **Task 6.2.9**: Similar tests for SearchXNGWebSearchTool

**File**: `tests/unit/tools/test_web_search.py`
- **Task 6.2.10**: Test `WebSearchTool.name` property returns `"duckduckgo"`
- **Task 6.2.11**: Test `WebSearchTool.search()` returns `list[Evidence]`
- **Task 6.2.12**: Test `WebSearchTool.search()` with mocked DDGS
- **Task 6.2.13**: Test error handling
- **Task 6.2.14**: Test query preprocessing

#### Activity 6.3: Integration Tests
**File**: `tests/integration/test_web_search_integration.py`
- **Task 6.3.1**: Test `SerperWebSearchTool` with real API (marked `@pytest.mark.integration`)
- **Task 6.3.2**: Test `SearchXNGWebSearchTool` with real API (marked `@pytest.mark.integration`)
- **Task 6.3.3**: Test `WebSearchTool` with real DuckDuckGo (marked `@pytest.mark.integration`)
- **Task 6.3.4**: Test `create_web_search_tool()` factory function
- **Task 6.3.5**: Test SearchHandler with web search tool

#### Activity 6.4: Update Existing Tests
**File**: `tests/unit/agents/test_retrieval_agent.py`
- **Task 6.4.1**: Update tests to expect `list[Evidence]` instead of `SearchResult`
- **Task 6.4.2**: Mock `WebSearchTool.search()` to return `list[Evidence]`

**File**: `tests/unit/tools/test_tool_executor.py`
- **Task 6.4.3**: Verify tests still pass with updated `web_search_adapter`

---

## Implementation Order

1. **PROJECT 1**: Vendor core components (foundation)
2. **PROJECT 3**: Fix existing WebSearchTool (quick win, unblocks retrieval agent)
3. **PROJECT 2**: Create SerperWebSearchTool (new functionality)
4. **PROJECT 4**: Integrate into SearchHandler (main integration)
5. **PROJECT 5**: Update callers (cleanup dependencies)
6. **PROJECT 6**: Testing (validation)

---

## Dependencies and Prerequisites

### External Dependencies
- `aiohttp` - Already in requirements
- `beautifulsoup4` - Already in requirements
- `duckduckgo-search` - Already in requirements
- `tenacity` - Already in requirements
- `structlog` - Already in requirements

### Internal Dependencies
- `src/tools/base.py` - SearchTool protocol
- `src/tools/rate_limiter.py` - Rate limiting utilities
- `src/tools/query_utils.py` - Query preprocessing
- `src/utils/config.py` - Settings and configuration
- `src/utils/exceptions.py` - Custom exceptions
- `src/utils/models.py` - Evidence, Citation models

### Configuration Requirements
- `SERPER_API_KEY` - For Serper provider
- `SEARCHXNG_HOST` - For SearchXNG provider
- `WEB_SEARCH_PROVIDER` - Environment variable (default: "duckduckgo")

---

## Risk Assessment

### High Risk
- **Breaking changes to retrieval_agent.py**: Must update carefully to handle `list[Evidence]` instead of `SearchResult`
- **Legacy folder dependencies**: Need to ensure all code is properly vendored

### Medium Risk
- **Rate limiting**: Serper API may have different limits than expected
- **Error handling**: Need to handle API failures gracefully

### Low Risk
- **Query preprocessing**: May need adjustment for web search vs PubMed
- **Testing**: Integration tests require API keys

---

## Success Criteria

1. ✅ `SerperWebSearchTool` implements `SearchTool` protocol correctly
2. ✅ `WebSearchTool` implements `SearchTool` protocol correctly
3. ✅ Both tools can be added to `SearchHandler`
4. ✅ `web_search_adapter` works with new implementation
5. ✅ `retrieval_agent` works with updated `WebSearchTool`
6. ✅ All unit tests pass
7. ✅ Integration tests pass (with API keys)
8. ✅ No dependencies on `folder/tools/web_search.py` in `src/` code
9. ✅ Configuration supports multiple providers
10. ✅ Error handling is robust

---

## Notes

- The vendored code should be self-contained and not depend on `folder/` modules
- Filter agent functionality from original code is removed (can be added later if needed)
- Rate limiting follows the same pattern as PubMed tool
- Query preprocessing may need web-specific adjustments (less aggressive than PubMed)
- Consider adding relevance scoring in the future


