# Services Architecture

DeepCritical provides several services for embeddings, RAG, and statistical analysis.

## Embedding Service

**File**: `src/services/embeddings.py`

**Purpose**: Local sentence-transformers for semantic search and deduplication

**Features**:
- **No API Key Required**: Uses local sentence-transformers models
- **Async-Safe**: All operations use `run_in_executor()` to avoid blocking the event loop
- **ChromaDB Storage**: In-memory vector storage for embeddings
- **Deduplication**: 0.9 similarity threshold by default (90% similarity = duplicate, configurable)

**Model**: Configurable via `settings.local_embedding_model` (default: `all-MiniLM-L6-v2`)

**Methods**:
- `async def embed(text: str) -> list[float]`: Generate embeddings (async-safe via `run_in_executor()`)
- `async def embed_batch(texts: list[str]) -> list[list[float]]`: Batch embedding (more efficient)
- `async def add_evidence(evidence_id: str, content: str, metadata: dict[str, Any]) -> None`: Add evidence to vector store
- `async def search_similar(query: str, n_results: int = 5) -> list[dict[str, Any]]`: Find semantically similar evidence
- `async def deduplicate(new_evidence: list[Evidence], threshold: float = 0.9) -> list[Evidence]`: Remove semantically duplicate evidence

**Usage**:
```python
from src.services.embeddings import get_embedding_service

service = get_embedding_service()
embedding = await service.embed("text to embed")
```

## LlamaIndex RAG Service

**File**: `src/services/llamaindex_rag.py`

**Purpose**: Retrieval-Augmented Generation using LlamaIndex

**Features**:
- **Multiple Embedding Providers**: OpenAI embeddings (requires `OPENAI_API_KEY`) or local sentence-transformers (no API key)
- **Multiple LLM Providers**: HuggingFace LLM (preferred) or OpenAI LLM (fallback) for query synthesis
- **ChromaDB Storage**: Vector database for document storage (supports in-memory mode)
- **Metadata Preservation**: Preserves source, title, URL, date, authors
- **Lazy Initialization**: Graceful fallback if dependencies not available

**Initialization Parameters**:
- `use_openai_embeddings: bool | None`: Force OpenAI embeddings (None = auto-detect)
- `use_in_memory: bool`: Use in-memory ChromaDB client (useful for tests)
- `oauth_token: str | None`: Optional OAuth token from HuggingFace login (takes priority over env vars)

**Methods**:
- `async def ingest_evidence(evidence: list[Evidence]) -> None`: Ingest evidence into RAG
- `async def retrieve(query: str, top_k: int = 5) -> list[Document]`: Retrieve relevant documents
- `async def query(query: str, top_k: int = 5) -> str`: Query with RAG

**Usage**:
```python
from src.services.llamaindex_rag import get_rag_service

service = get_rag_service(
    use_openai_embeddings=False,  # Use local embeddings
    use_in_memory=True,  # Use in-memory ChromaDB
    oauth_token=token  # Optional HuggingFace token
)
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

Services use singleton patterns for lazy initialization:

**EmbeddingService**: Uses a global variable pattern:

<!--codeinclude-->
[EmbeddingService Singleton](../src/services/embeddings.py) start_line:164 end_line:172
<!--/codeinclude-->

**LlamaIndexRAGService**: Direct instantiation (no caching):

<!--codeinclude-->
[LlamaIndexRAGService Factory](../src/services/llamaindex_rag.py) start_line:440 end_line:466
<!--/codeinclude-->

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

