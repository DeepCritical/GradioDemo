# Services API Reference

This page documents the API for DeepCritical services.

## EmbeddingService

**Module**: `src.services.embeddings`

**Purpose**: Local sentence-transformers for semantic search and deduplication.

### Methods

#### `embed`

```python
async def embed(self, text: str) -> list[float]
```

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

```python
async def ingest_evidence(self, evidence: list[Evidence]) -> None
```

Ingests evidence into RAG service.

**Parameters**:
- `evidence`: List of Evidence objects to ingest

**Note**: Requires OpenAI API key for embeddings.

#### `retrieve`

```python
async def retrieve(
    self,
    query: str,
    top_k: int = 5
) -> list[Document]
```

Retrieves relevant documents for a query.

**Parameters**:
- `query`: Search query string
- `top_k`: Number of top results to return (default: 5)

**Returns**: List of Document objects with metadata.

#### `query`

```python
async def query(
    self,
    query: str,
    top_k: int = 5
) -> str
```

Queries RAG service and returns formatted results.

**Parameters**:
- `query`: Search query string
- `top_k`: Number of top results to return (default: 5)

**Returns**: Formatted query results as string.

### Factory Function

#### `get_rag_service`

```python
@lru_cache(maxsize=1)
def get_rag_service() -> LlamaIndexRAGService | None
```

Returns singleton LlamaIndexRAGService instance, or None if OpenAI key not available.

## StatisticalAnalyzer

**Module**: `src.services.statistical_analyzer`

**Purpose**: Secure execution of AI-generated statistical code.

### Methods

#### `analyze`

```python
async def analyze(
    self,
    hypothesis: str,
    evidence: list[Evidence],
    data_description: str | None = None
) -> AnalysisResult
```

Analyzes a hypothesis using statistical methods.

**Parameters**:
- `hypothesis`: Hypothesis to analyze
- `evidence`: List of Evidence objects
- `data_description`: Optional data description

**Returns**: `AnalysisResult` with:
- `verdict`: SUPPORTED, REFUTED, or INCONCLUSIVE
- `code`: Generated analysis code
- `output`: Execution output
- `error`: Error message if execution failed

**Note**: Requires Modal credentials for sandbox execution.

## See Also

- [Architecture - Services](../architecture/services.md) - Architecture overview
- [Configuration](../configuration/index.md) - Service configuration
























