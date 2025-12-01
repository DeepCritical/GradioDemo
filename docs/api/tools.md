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
- `SearchError`: If search fails
- `RateLimitError`: If rate limit is exceeded

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

**Note**: Only returns interventional studies with status: COMPLETED, ACTIVE_NOT_RECRUITING, RECRUITING, ENROLLING_BY_INVITATION

**Raises**:
- `SearchError`: If search fails

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

**Note**: Includes both preprints (marked with `[PREPRINT - Not peer-reviewed]`) and peer-reviewed articles.

**Raises**:
- `SearchError`: If search fails

## RAGTool

**Module**: `src.tools.rag_tool`

**Purpose**: Semantic search within collected evidence.

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

**Note**: Requires evidence to be ingested into RAG service first.

## SearchHandler

**Module**: `src.tools.search_handler`

**Purpose**: Orchestrates parallel searches across multiple tools.

### Methods

#### `search`

```python
async def search(
    self,
    query: str,
    tools: list[SearchTool] | None = None,
    max_results_per_tool: int = 10
) -> SearchResult
```

Searches multiple tools in parallel.

**Parameters**:
- `query`: Search query string
- `tools`: List of tools to use (default: all available tools)
- `max_results_per_tool`: Maximum results per tool (default: 10)

**Returns**: `SearchResult` with:
- `evidence`: Aggregated list of evidence
- `tool_results`: Results per tool
- `total_count`: Total number of results

**Note**: Uses `asyncio.gather()` for parallel execution. Handles tool failures gracefully.

## See Also

- [Architecture - Tools](../architecture/tools.md) - Architecture overview
- [Models API](models.md) - Data models used by tools



















