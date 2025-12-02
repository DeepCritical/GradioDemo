# Services API Reference

This page documents the API for DeepCritical services.

## EmbeddingService

**Module**: `src.services.embeddings`

**Purpose**: Local sentence-transformers for semantic search and deduplication.

### Methods

#### `embed`

<!--codeinclude-->
[EmbeddingService.embed](../src/services/embeddings.py) start_line:55 end_line:55
<!--/codeinclude-->

Generates embedding for a text string.

**Parameters**:
- `text`: Text to embed

**Returns**: Embedding vector as list of floats.

#### `embed_batch`

```python
async def embed_batch(self, texts: list[str]) -> list[list[float]]
```

Generates embeddings for multiple texts.

**Parameters**:
- `texts`: List of texts to embed

**Returns**: List of embedding vectors.

#### `similarity`

```python
async def similarity(self, text1: str, text2: str) -> float
```

Calculates similarity between two texts.

**Parameters**:
- `text1`: First text
- `text2`: Second text

**Returns**: Similarity score (0.0-1.0).

#### `find_duplicates`

```python
async def find_duplicates(
    self,
    texts: list[str],
    threshold: float = 0.85
) -> list[tuple[int, int]]
```

Finds duplicate texts based on similarity threshold.

**Parameters**:
- `texts`: List of texts to check
- `threshold`: Similarity threshold (default: 0.85)

**Returns**: List of (index1, index2) tuples for duplicate pairs.

#### `add_evidence`

```python
async def add_evidence(
    self,
    evidence_id: str,
    content: str,
    metadata: dict[str, Any]
) -> None
```

Adds evidence to vector store for semantic search.

**Parameters**:
- `evidence_id`: Unique identifier for the evidence
- `content`: Evidence text content
- `metadata`: Additional metadata dictionary

#### `search_similar`

```python
async def search_similar(
    self,
    query: str,
    n_results: int = 5
) -> list[dict[str, Any]]
```

Finds semantically similar evidence.

**Parameters**:
- `query`: Search query string
- `n_results`: Number of results to return (default: 5)

**Returns**: List of dictionaries with `id`, `content`, `metadata`, and `distance` keys.

#### `deduplicate`

```python
async def deduplicate(
    self,
    new_evidence: list[Evidence],
    threshold: float = 0.9
) -> list[Evidence]
```

Removes semantically duplicate evidence.

**Parameters**:
- `new_evidence`: List of evidence items to deduplicate
- `threshold`: Similarity threshold (default: 0.9, where 0.9 = 90% similar is duplicate)

**Returns**: List of unique evidence items (not already in vector store).

### Factory Function

#### `get_embedding_service`

```python
@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService
```

Returns singleton EmbeddingService instance.

## LlamaIndexRAGService

**Module**: `src.services.rag`

**Purpose**: Retrieval-Augmented Generation using LlamaIndex.

### Methods

#### `ingest_evidence`

<!--codeinclude-->
[LlamaIndexRAGService.ingest_evidence](../src/services/llamaindex_rag.py) start_line:290 end_line:290
<!--/codeinclude-->

Ingests evidence into RAG service.

**Parameters**:
- `evidence_list`: List of Evidence objects to ingest

**Note**: Supports multiple embedding providers (OpenAI, local sentence-transformers, Hugging Face).

#### `retrieve`

```python
def retrieve(
    self,
    query: str,
    top_k: int | None = None
) -> list[dict[str, Any]]
```

Retrieves relevant documents for a query.

**Parameters**:
- `query`: Search query string
- `top_k`: Number of top results to return (defaults to `similarity_top_k` from constructor)

**Returns**: List of dictionaries with `text`, `score`, and `metadata` keys.

#### `query`

```python
def query(
    self,
    query_str: str,
    top_k: int | None = None
) -> str
```

Queries RAG service and returns synthesized response.

**Parameters**:
- `query_str`: Query string
- `top_k`: Number of results to use (defaults to `similarity_top_k` from constructor)

**Returns**: Synthesized response string.

**Raises**:
- `ConfigurationError`: If no LLM API key is available for query synthesis

#### `ingest_documents`

```python
def ingest_documents(self, documents: list[Any]) -> None
```

Ingests raw LlamaIndex Documents.

**Parameters**:
- `documents`: List of LlamaIndex Document objects

#### `clear_collection`

```python
def clear_collection(self) -> None
```

Clears all documents from the collection.

### Factory Function

#### `get_rag_service`

```python
def get_rag_service(
    collection_name: str = "deepcritical_evidence",
    oauth_token: str | None = None,
    **kwargs: Any
) -> LlamaIndexRAGService
```

Get or create a RAG service instance.

**Parameters**:
- `collection_name`: Name of the ChromaDB collection (default: "deepcritical_evidence")
- `oauth_token`: Optional OAuth token from HuggingFace login (takes priority over env vars)
- `**kwargs`: Additional arguments for LlamaIndexRAGService (e.g., `use_openai_embeddings=False`)

**Returns**: Configured LlamaIndexRAGService instance.

**Note**: By default, uses local embeddings (sentence-transformers) which require no API keys.

## StatisticalAnalyzer

**Module**: `src.services.statistical_analyzer`

**Purpose**: Secure execution of AI-generated statistical code.

### Methods

#### `analyze`

```python
async def analyze(
    self,
    query: str,
    evidence: list[Evidence],
    hypothesis: dict[str, Any] | None = None
) -> AnalysisResult
```

Analyzes a research question using statistical methods.

**Parameters**:
- `query`: The research question
- `evidence`: List of Evidence objects to analyze
- `hypothesis`: Optional hypothesis dict with `drug`, `target`, `pathway`, `effect`, `confidence` keys

**Returns**: `AnalysisResult` with:
- `verdict`: SUPPORTED, REFUTED, or INCONCLUSIVE
- `confidence`: Confidence in verdict (0.0-1.0)
- `statistical_evidence`: Summary of statistical findings
- `code_generated`: Python code that was executed
- `execution_output`: Output from code execution
- `key_takeaways`: Key takeaways from analysis
- `limitations`: List of limitations

**Note**: Requires Modal credentials for sandbox execution.

## See Also

- [Architecture - Services](../architecture/services.md) - Architecture overview
- [Configuration](../configuration/index.md) - Service configuration

