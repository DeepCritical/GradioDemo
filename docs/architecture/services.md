# Services Architecture

DeepCritical provides several services for embeddings, RAG, and statistical analysis.

## Embedding Service

**File**: `src/services/embeddings.py`

**Purpose**: Local sentence-transformers for semantic search and deduplication

**Features**:
- **No API Key Required**: Uses local sentence-transformers models
- **Async-Safe**: All operations use `run_in_executor()` to avoid blocking
- **ChromaDB Storage**: Vector storage for embeddings
- **Deduplication**: 0.85 similarity threshold (85% similarity = duplicate)

**Model**: Configurable via `settings.local_embedding_model` (default: `all-MiniLM-L6-v2`)

**Methods**:
- `async def embed(text: str) -> list[float]`: Generate embeddings
- `async def embed_batch(texts: list[str]) -> list[list[float]]`: Batch embedding
- `async def similarity(text1: str, text2: str) -> float`: Calculate similarity
- `async def find_duplicates(texts: list[str], threshold: float = 0.85) -> list[tuple[int, int]]`: Find duplicates

**Usage**:
```python
from src.services.embeddings import get_embedding_service

service = get_embedding_service()
embedding = await service.embed("text to embed")
```

## LlamaIndex RAG Service

**File**: `src/services/rag.py`

**Purpose**: Retrieval-Augmented Generation using LlamaIndex

**Features**:
- **OpenAI Embeddings**: Requires `OPENAI_API_KEY`
- **ChromaDB Storage**: Vector database for document storage
- **Metadata Preservation**: Preserves source, title, URL, date, authors
- **Lazy Initialization**: Graceful fallback if OpenAI key not available

**Methods**:
- `async def ingest_evidence(evidence: list[Evidence]) -> None`: Ingest evidence into RAG
- `async def retrieve(query: str, top_k: int = 5) -> list[Document]`: Retrieve relevant documents
- `async def query(query: str, top_k: int = 5) -> str`: Query with RAG

**Usage**:
```python
from src.services.rag import get_rag_service

service = get_rag_service()
if service:
    documents = await service.retrieve("query", top_k=5)
```

## Statistical Analyzer

**File**: `src/services/statistical_analyzer.py`

**Purpose**: Secure execution of AI-generated statistical code

**Features**:
- **Modal Sandbox**: Secure, isolated execution environment
- **Code Generation**: Generates Python code via LLM
- **Library Pinning**: Version-pinned libraries in `SANDBOX_LIBRARIES`
- **Network Isolation**: `block_network=True` by default

**Libraries Available**:
- pandas, numpy, scipy
- matplotlib, scikit-learn
- statsmodels

**Output**: `AnalysisResult` with:
- `verdict`: SUPPORTED, REFUTED, or INCONCLUSIVE
- `code`: Generated analysis code
- `output`: Execution output
- `error`: Error message if execution failed

**Usage**:
```python
from src.services.statistical_analyzer import StatisticalAnalyzer

analyzer = StatisticalAnalyzer()
result = await analyzer.analyze(
    hypothesis="Metformin reduces cancer risk",
    evidence=evidence_list
)
```

## Singleton Pattern

All services use the singleton pattern with `@lru_cache(maxsize=1)`:

```python
@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
```

This ensures:
- Single instance per process
- Lazy initialization
- No dependencies required at import time

## Service Availability

Services check availability before use:

```python
from src.utils.config import settings

if settings.modal_available:
    # Use Modal sandbox
    pass

if settings.has_openai_key:
    # Use OpenAI embeddings for RAG
    pass
```

## See Also

- [Tools](tools.md) - How services are used by search tools
- [API Reference - Services](../api/services.md) - API documentation
- [Configuration](../configuration/index.md) - Service configuration

















