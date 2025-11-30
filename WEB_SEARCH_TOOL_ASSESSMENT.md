# Web Search Tool Assessment

## Executive Summary

The application has **two separate web search implementations** with different readiness levels:

1. **`WebSearchTool`** (`src/tools/web_search.py`) - **Partially Ready** ⚠️
   - Functional but **NOT compliant** with `SearchTool` protocol
   - **NOT integrated** into main search handler
   - Only used in magentic orchestrator's retrieval agent

2. **`web_search_adapter`** (`src/tools/web_search_adapter.py`) - **Functional** ✅
   - Used by tool executor for WebSearchAgent tasks
   - Relies on legacy `folder/tools/web_search.py` implementation

## Detailed Analysis

### 1. WebSearchTool (`src/tools/web_search.py`)

#### Current Implementation
- **Location**: `src/tools/web_search.py`
- **Provider**: DuckDuckGo (no API key required)
- **Status**: ⚠️ **Partially Ready**

#### Issues Identified

**❌ Protocol Non-Compliance:**
```python
# Missing required 'name' property
class WebSearchTool:
    # Should have: @property def name(self) -> str: return "web"
    
    # Wrong return type - should return list[Evidence], not SearchResult
    async def search(self, query: str, max_results: int = 10) -> SearchResult:
        # Returns SearchResult instead of list[Evidence]
```

**Comparison with other tools:**
- `PubMedTool` has `@property def name(self) -> str: return "pubmed"`
- `PubMedTool.search()` returns `list[Evidence]`
- `WebSearchTool` returns `SearchResult` (contains `evidence` list inside)

**❌ Not Integrated:**
- **NOT** included in `SearchHandler` initialization in `src/app.py`:
  ```python
  search_handler = SearchHandler(
      tools=[PubMedTool(), ClinicalTrialsTool(), EuropePMCTool()],
      # WebSearchTool() is missing!
  )
  ```

**✅ Current Usage:**
- Used in `src/agents/retrieval_agent.py` (magentic orchestrator):
  ```python
  from src.tools.web_search import WebSearchTool
  _web_search = WebSearchTool()
  ```

#### Fix Required
To make `WebSearchTool` compliant and usable:

1. **Add `name` property:**
   ```python
   @property
   def name(self) -> str:
       return "web"
   ```

2. **Fix return type:**
   ```python
   async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
       # ... existing code ...
       return evidence  # Return list[Evidence] directly, not SearchResult
   ```

3. **Register in SearchHandler:**
   ```python
   from src.tools.web_search import WebSearchTool
   
   search_handler = SearchHandler(
       tools=[
           PubMedTool(), 
           ClinicalTrialsTool(), 
           EuropePMCTool(),
           WebSearchTool()  # Add this
       ],
   )
   ```

---

### 2. web_search_adapter (`src/tools/web_search_adapter.py`)

#### Current Implementation
- **Location**: `src/tools/web_search_adapter.py`
- **Status**: ✅ **Functional**
- **Provider**: Uses legacy `folder/tools/web_search.py` (Serper/SearchXNG)

#### Usage
- Used by `src/tools/tool_executor.py` for `WebSearchAgent` tasks:
  ```python
  if task.agent == "WebSearchAgent":
      result_text = await web_search(task.query)
  ```

- Used by `src/orchestrator/planner_agent.py` for background context

#### Dependencies
- Requires `folder/tools/web_search.py` (legacy implementation)
- Supports Serper API (requires `SERPER_API_KEY`)
- Supports SearchXNG API (requires `SEARCHXNG_HOST`)

#### Limitations
- Returns formatted string (not `Evidence` objects)
- Not integrated with `SearchHandler` (different execution path)
- Depends on legacy folder structure

---

## Integration Status

### SearchHandler Integration
**Current State**: ❌ **NOT Integrated**

The main `SearchHandler` in `src/app.py` only includes:
- `PubMedTool()`
- `ClinicalTrialsTool()`
- `EuropePMCTool()`

**WebSearchTool is missing from the main search flow.**

### Tool Executor Integration
**Current State**: ✅ **Integrated**

`web_search_adapter` is used via `tool_executor.py`:
- Executes when `AgentTask.agent == "WebSearchAgent"`
- Used in iterative/deep research flows
- Returns formatted text (not Evidence objects)

### Magentic Orchestrator Integration
**Current State**: ✅ **Integrated**

`WebSearchTool` is used in `retrieval_agent.py`:
- Direct instantiation: `_web_search = WebSearchTool()`
- Used via `search_web()` function
- Updates workflow state with evidence

---

## Can It Be Used?

### WebSearchTool (`src/tools/web_search.py`)
**Status**: ⚠️ **Can be used, but with limitations**

**Can be used:**
- ✅ In magentic orchestrator (already working)
- ✅ As standalone tool (functional)

**Cannot be used:**
- ❌ In `SearchHandler` (protocol non-compliance)
- ❌ In parallel search flows (not registered)

**To make fully usable:**
1. Fix protocol compliance (add `name`, fix return type)
2. Register in `SearchHandler`
3. Test integration

### web_search_adapter
**Status**: ✅ **Can be used**

**Can be used:**
- ✅ Via `tool_executor` for WebSearchAgent tasks
- ✅ In planner agent for background context
- ✅ In iterative/deep research flows

**Limitations:**
- Returns string format (not Evidence objects)
- Requires legacy folder dependencies
- Different execution path than SearchHandler

---

## Recommendations

### Priority 1: Fix WebSearchTool Protocol Compliance
Make `WebSearchTool` fully compliant with `SearchTool` protocol:

1. Add `name` property
2. Change return type from `SearchResult` to `list[Evidence]`
3. Update all callers if needed

### Priority 2: Integrate into SearchHandler
Add `WebSearchTool` to main search flow:

```python
from src.tools.web_search import WebSearchTool

search_handler = SearchHandler(
    tools=[
        PubMedTool(), 
        ClinicalTrialsTool(), 
        EuropePMCTool(),
        WebSearchTool()  # Add web search
    ],
)
```

### Priority 3: Consolidate Implementations
Consider consolidating the two implementations:
- Keep `WebSearchTool` as the main implementation
- Deprecate or migrate `web_search_adapter` usage
- Remove dependency on `folder/tools/web_search.py`

### Priority 4: Testing
Add tests for:
- Protocol compliance
- SearchHandler integration
- Error handling
- Rate limiting (if needed)

---

## Summary Table

| Component | Status | Protocol Compliant | Integrated | Can Be Used |
|-----------|--------|-------------------|------------|-------------|
| `WebSearchTool` | ⚠️ Partial | ❌ No | ❌ No | ⚠️ Limited |
| `web_search_adapter` | ✅ Functional | N/A | ✅ Yes (tool_executor) | ✅ Yes |

---

## Conclusion

The web search functionality exists in two forms:
1. **`WebSearchTool`** is functional but needs protocol fixes to be fully integrated
2. **`web_search_adapter`** is working but uses a different execution path

**Recommendation**: Fix `WebSearchTool` protocol compliance and integrate it into `SearchHandler` for unified search capabilities across all orchestrators.

