# Tools API Reference

This page documents the API for DeepCritical search tools.

## SearchTool Protocol

All tools implement the `SearchTool` protocol:

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

## PubMedTool

**Module**: `src.tools.pubmed`

**Purpose**: Search peer-reviewed biomedical literature from PubMed.

### Properties

#### `name`

```python
@property
def name(self) -> str
```

Returns tool name: `"pubmed"`

### Methods

#### `search`

```python
async def search(
    self,
    query: str,
    max_results: int = 10
) -> list[Evidence]
```

Searches PubMed for articles.

**Parameters**:
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 10)

**Returns**: List of `Evidence` objects with PubMed articles.

**Raises**:
- `SearchError`: If search fails (timeout, HTTP error, XML parsing error)
- `RateLimitError`: If rate limit is exceeded (429 status code)

**Note**: Uses NCBI E-utilities (ESearch → EFetch). Rate limit: 0.34s between requests. Handles single vs. multiple articles.

## ClinicalTrialsTool

**Module**: `src.tools.clinicaltrials`

**Purpose**: Search ClinicalTrials.gov for interventional studies.

### Properties

#### `name`

```python
@property
def name(self) -> str
```

Returns tool name: `"clinicaltrials"`

### Methods

#### `search`

```python
async def search(
    self,
    query: str,
    max_results: int = 10
) -> list[Evidence]
```

Searches ClinicalTrials.gov for trials.

**Parameters**:
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 10)

**Returns**: List of `Evidence` objects with clinical trials.

**Note**: Only returns interventional studies with status: COMPLETED, ACTIVE_NOT_RECRUITING, RECRUITING, ENROLLING_BY_INVITATION. Uses `requests` library (NOT httpx - WAF blocks httpx). Runs in thread pool for async compatibility.

**Raises**:
- `SearchError`: If search fails (HTTP error, request exception)

## EuropePMCTool

**Module**: `src.tools.europepmc`

**Purpose**: Search Europe PMC for preprints and peer-reviewed articles.

### Properties

#### `name`

```python
@property
def name(self) -> str
```

Returns tool name: `"europepmc"`

### Methods

#### `search`

```python
async def search(
    self,
    query: str,
    max_results: int = 10
) -> list[Evidence]
```

Searches Europe PMC for articles and preprints.

**Parameters**:
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 10)

**Returns**: List of `Evidence` objects with articles/preprints.

**Note**: Includes both preprints (marked with `[PREPRINT - Not peer-reviewed]`) and peer-reviewed articles. Handles preprint markers. Builds URLs from DOI or PMID.

**Raises**:
- `SearchError`: If search fails (HTTP error, connection error)

## RAGTool

**Module**: `src.tools.rag_tool`

**Purpose**: Semantic search within collected evidence.

### Initialization

```python
def __init__(
    self,
    rag_service: LlamaIndexRAGService | None = None,
    oauth_token: str | None = None
) -> None
```

**Parameters**:
- `rag_service`: Optional RAG service instance. If None, will be lazy-initialized.
- `oauth_token`: Optional OAuth token from HuggingFace login (for RAG LLM)

### Properties

#### `name`

```python
@property
def name(self) -> str
```

Returns tool name: `"rag"`

### Methods

#### `search`

```python
async def search(
    self,
    query: str,
    max_results: int = 10
) -> list[Evidence]
```

Searches collected evidence using semantic similarity.

**Parameters**:
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 10)

**Returns**: List of `Evidence` objects from collected evidence.

**Raises**:
- `ConfigurationError`: If RAG service is unavailable

**Note**: Requires evidence to be ingested into RAG service first. Wraps `LlamaIndexRAGService`. Returns Evidence from RAG results.

## SearchHandler

**Module**: `src.tools.search_handler`

**Purpose**: Orchestrates parallel searches across multiple tools.

### Initialization

```python
def __init__(
    self,
    tools: list[SearchTool],
    timeout: float = 30.0,
    include_rag: bool = False,
    auto_ingest_to_rag: bool = True,
    oauth_token: str | None = None
) -> None
```

**Parameters**:
- `tools`: List of search tools to use
- `timeout`: Timeout for each search in seconds (default: 30.0)
- `include_rag`: Whether to include RAG tool in searches (default: False)
- `auto_ingest_to_rag`: Whether to automatically ingest results into RAG (default: True)
- `oauth_token`: Optional OAuth token from HuggingFace login (for RAG LLM)

### Methods

#### `execute`

<!--codeinclude-->
[SearchHandler.execute](../src/tools/search_handler.py) start_line:86 end_line:86
<!--/codeinclude-->

Searches multiple tools in parallel.

**Parameters**:
- `query`: Search query string
- `max_results_per_tool`: Maximum results per tool (default: 10)

**Returns**: `SearchResult` with:
- `query`: The search query
- `evidence`: Aggregated list of evidence
- `sources_searched`: List of source names searched
- `total_found`: Total number of results
- `errors`: List of error messages from failed tools

**Raises**:
- `SearchError`: If search times out

**Note**: Uses `asyncio.gather()` for parallel execution. Handles tool failures gracefully (returns errors in `SearchResult.errors`). Automatically ingests evidence into RAG if enabled.

## See Also

- [Architecture - Tools](../architecture/tools.md) - Architecture overview
- [Models API](models.md) - Data models used by tools
