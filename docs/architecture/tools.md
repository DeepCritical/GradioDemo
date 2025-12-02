# Tools Architecture

DeepCritical implements a protocol-based search tool system for retrieving evidence from multiple sources.

## SearchTool Protocol

All tools implement the `SearchTool` protocol from `src/tools/base.py`:

<!--codeinclude-->
[SearchTool Protocol](../src/tools/base.py) start_line:8 end_line:31
<!--/codeinclude-->

## Rate Limiting

All tools use the `@retry` decorator from tenacity:

<!--codeinclude-->
[Retry Decorator Pattern](../src/tools/pubmed.py) start_line:46 end_line:50
<!--/codeinclude-->

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

**Initialization Parameters**:
- `tools: list[SearchTool]`: List of search tools to use
- `timeout: float = 30.0`: Timeout for each search in seconds
- `include_rag: bool = False`: Whether to include RAG tool in searches
- `auto_ingest_to_rag: bool = True`: Whether to automatically ingest results into RAG
- `oauth_token: str | None = None`: Optional OAuth token from HuggingFace login (for RAG LLM)

**Methods**:
- `async def execute(query: str, max_results_per_tool: int = 10) -> SearchResult`: Execute search across all tools in parallel

**Features**:
- Uses `asyncio.gather()` with `return_exceptions=True` for parallel execution
- Aggregates results into `SearchResult` with evidence and metadata
- Handles tool failures gracefully (continues with other tools)
- Deduplicates results by URL
- Automatically ingests results into RAG if `auto_ingest_to_rag=True`
- Can add RAG tool dynamically via `add_rag_tool()` method

## Tool Registration

Tools are registered in the search handler:

```python
from src.tools.pubmed import PubMedTool
from src.tools.clinicaltrials import ClinicalTrialsTool
from src.tools.europepmc import EuropePMCTool
from src.tools.search_handler import SearchHandler

search_handler = SearchHandler(
    tools=[
        PubMedTool(),
        ClinicalTrialsTool(),
        EuropePMCTool(),
    ],
    include_rag=True,  # Include RAG tool for semantic search
    auto_ingest_to_rag=True,  # Automatically ingest results into RAG
    oauth_token=token  # Optional HuggingFace token for RAG LLM
)

# Execute search
result = await search_handler.execute("query", max_results_per_tool=10)
```

## See Also

- [Services](services.md) - RAG and embedding services
- [API Reference - Tools](../api/tools.md) - API documentation
- [Contributing - Implementation Patterns](../contributing/implementation-patterns.md) - Development guidelines
