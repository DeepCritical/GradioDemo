# Tools Architecture

DeepCritical implements a protocol-based search tool system for retrieving evidence from multiple sources.

## SearchTool Protocol

All tools implement the `SearchTool` protocol from `src/tools/base.py`:

```python
class SearchTool(Protocol):
    @property
    def name(self) -> str: ...
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10
    ) -> list[Evidence]: ...
```

## Rate Limiting

All tools use the `@retry` decorator from tenacity:

```python
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(...)
)
async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
    # Implementation
```

Tools with API rate limits implement `_rate_limit()` method and use shared rate limiters from `src/tools/rate_limiter.py`.

## Error Handling

Tools raise custom exceptions:

- `SearchError`: General search failures
- `RateLimitError`: Rate limit exceeded

Tools handle HTTP errors (429, 500, timeout) and return empty lists on non-critical errors (with warning logs).

## Query Preprocessing

Tools use `preprocess_query()` from `src/tools/query_utils.py` to:

- Remove noise from queries
- Expand synonyms
- Normalize query format

## Evidence Conversion

All tools convert API responses to `Evidence` objects with:

- `Citation`: Title, URL, date, authors
- `content`: Evidence text
- `relevance_score`: 0.0-1.0 relevance score
- `metadata`: Additional metadata

Missing fields are handled gracefully with defaults.

## Tool Implementations

### PubMed Tool

**File**: `src/tools/pubmed.py`

**API**: NCBI E-utilities (ESearch → EFetch)

**Rate Limiting**: 
- 0.34s between requests (3 req/sec without API key)
- 0.1s between requests (10 req/sec with NCBI API key)

**Features**:
- XML parsing with `xmltodict`
- Handles single vs. multiple articles
- Query preprocessing
- Evidence conversion with metadata extraction

### ClinicalTrials Tool

**File**: `src/tools/clinicaltrials.py`

**API**: ClinicalTrials.gov API v2

**Important**: Uses `requests` library (NOT httpx) because WAF blocks httpx TLS fingerprint.

**Execution**: Runs in thread pool: `await asyncio.to_thread(requests.get, ...)`

**Filtering**:
- Only interventional studies
- Status: `COMPLETED`, `ACTIVE_NOT_RECRUITING`, `RECRUITING`, `ENROLLING_BY_INVITATION`

**Features**:
- Parses nested JSON structure
- Extracts trial metadata
- Evidence conversion

### Europe PMC Tool

**File**: `src/tools/europepmc.py`

**API**: Europe PMC REST API

**Features**:
- Handles preprint markers: `[PREPRINT - Not peer-reviewed]`
- Builds URLs from DOI or PMID
- Checks `pubTypeList` for preprint detection
- Includes both preprints and peer-reviewed articles

### RAG Tool

**File**: `src/tools/rag_tool.py`

**Purpose**: Semantic search within collected evidence

**Implementation**: Wraps `LlamaIndexRAGService`

**Features**:
- Returns Evidence from RAG results
- Handles evidence ingestion
- Semantic similarity search
- Metadata preservation

### Search Handler

**File**: `src/tools/search_handler.py`

**Purpose**: Orchestrates parallel searches across multiple tools

**Features**:
- Uses `asyncio.gather()` with `return_exceptions=True`
- Aggregates results into `SearchResult`
- Handles tool failures gracefully
- Deduplicates results by URL

## Tool Registration

Tools are registered in the search handler:

```python
from src.tools.pubmed import PubMedTool
from src.tools.clinicaltrials import ClinicalTrialsTool
from src.tools.europepmc import EuropePMCTool

search_handler = SearchHandler(
    tools=[
        PubMedTool(),
        ClinicalTrialsTool(),
        EuropePMCTool(),
    ]
)
```

## See Also

- [Services](services.md) - RAG and embedding services
- [API Reference - Tools](../api/tools.md) - API documentation
- [Contributing - Implementation Patterns](../contributing/implementation-patterns.md) - Development guidelines




















