# Configuration Guide

## Overview

DeepCritical uses **Pydantic Settings** for centralized configuration management. All settings are defined in the `Settings` class in `src/utils/config.py` and can be configured via environment variables or a `.env` file.

The configuration system provides:

- **Type Safety**: Strongly-typed fields with Pydantic validation
- **Environment File Support**: Automatically loads from `.env` file (if present)
- **Case-Insensitive**: Environment variables are case-insensitive
- **Singleton Pattern**: Global `settings` instance for easy access throughout the codebase
- **Validation**: Automatic validation on load with helpful error messages

## Quick Start

1. Create a `.env` file in the project root
2. Set at least one LLM API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `HF_TOKEN`)
3. Optionally configure other services as needed
4. The application will automatically load and validate your configuration

## Configuration System Architecture

### Settings Class

The [`Settings`][settings-class] class extends `BaseSettings` from `pydantic_settings` and defines all application configuration:

```13:21:src/utils/config.py
class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
```

[View source](https://github.com/DeepCritical/GradioDemo/blob/main/src/utils/config.py#L13-L21)

### Singleton Instance

A global `settings` instance is available for import:

```234:235:src/utils/config.py
# Singleton for easy import
settings = get_settings()
```

[View source](https://github.com/DeepCritical/GradioDemo/blob/main/src/utils/config.py#L234-L235)

### Usage Pattern

Access configuration throughout the codebase:

```python
from src.utils.config import settings

# Check if API keys are available
if settings.has_openai_key:
    # Use OpenAI
    pass

# Access configuration values
max_iterations = settings.max_iterations
web_search_provider = settings.web_search_provider
```

## Required Configuration

### LLM Provider

You must configure at least one LLM provider. The system supports:

- **OpenAI**: Requires `OPENAI_API_KEY`
- **Anthropic**: Requires `ANTHROPIC_API_KEY`
- **HuggingFace**: Optional `HF_TOKEN` or `HUGGINGFACE_API_KEY` (can work without key for public models)

#### OpenAI Configuration

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.1
```

The default model is defined in the `Settings` class:

```29:29:src/utils/config.py
    openai_model: str = Field(default="gpt-5.1", description="OpenAI model name")
```

#### Anthropic Configuration

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

The default model is defined in the `Settings` class:

```30:32:src/utils/config.py
    anthropic_model: str = Field(
        default="claude-sonnet-4-5-20250929", description="Anthropic model"
    )
```

#### HuggingFace Configuration

HuggingFace can work without an API key for public models, but an API key provides higher rate limits:

```bash
# Option 1: Using HF_TOKEN (preferred)
HF_TOKEN=your_huggingface_token_here

# Option 2: Using HUGGINGFACE_API_KEY (alternative)
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Default model
HUGGINGFACE_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

The HuggingFace token can be set via either environment variable:

```33:35:src/utils/config.py
    hf_token: str | None = Field(
        default=None, alias="HF_TOKEN", description="HuggingFace API token"
    )
```

```57:59:src/utils/config.py
    huggingface_api_key: str | None = Field(
        default=None, description="HuggingFace API token (HF_TOKEN or HUGGINGFACE_API_KEY)"
    )
```

## Optional Configuration

### Embedding Configuration

DeepCritical supports multiple embedding providers for semantic search and RAG:

```bash
# Embedding Provider: "openai", "local", or "huggingface"
EMBEDDING_PROVIDER=local

# OpenAI Embedding Model (used by LlamaIndex RAG)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Local Embedding Model (sentence-transformers, used by EmbeddingService)
LOCAL_EMBEDDING_MODEL=all-MiniLM-L6-v2

# HuggingFace Embedding Model
HUGGINGFACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

The embedding provider configuration:

```47:50:src/utils/config.py
    embedding_provider: Literal["openai", "local", "huggingface"] = Field(
        default="local",
        description="Embedding provider to use",
    )
```

**Note**: OpenAI embeddings require `OPENAI_API_KEY`. The local provider (default) uses sentence-transformers and requires no API key.

### Web Search Configuration

DeepCritical supports multiple web search providers:

```bash
# Web Search Provider: "serper", "searchxng", "brave", "tavily", or "duckduckgo"
# Default: "duckduckgo" (no API key required)
WEB_SEARCH_PROVIDER=duckduckgo

# Serper API Key (for Google search via Serper)
SERPER_API_KEY=your_serper_api_key_here

# SearchXNG Host URL (for self-hosted search)
SEARCHXNG_HOST=http://localhost:8080

# Brave Search API Key
BRAVE_API_KEY=your_brave_api_key_here

# Tavily API Key
TAVILY_API_KEY=your_tavily_api_key_here
```

The web search provider configuration:

```71:74:src/utils/config.py
    web_search_provider: Literal["serper", "searchxng", "brave", "tavily", "duckduckgo"] = Field(
        default="duckduckgo",
        description="Web search provider to use",
    )
```

**Note**: DuckDuckGo is the default and requires no API key, making it ideal for development and testing.

### PubMed Configuration

PubMed search supports optional NCBI API key for higher rate limits:

```bash
# NCBI API Key (optional, for higher rate limits: 10 req/sec vs 3 req/sec)
NCBI_API_KEY=your_ncbi_api_key_here
```

The PubMed tool uses this configuration:

```22:29:src/tools/pubmed.py
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.ncbi_api_key
        # Ignore placeholder values from .env.example
        if self.api_key == "your-ncbi-key-here":
            self.api_key = None

        # Use shared rate limiter
        self._limiter = get_pubmed_limiter(self.api_key)
```

### Agent Configuration

Control agent behavior and research loop execution:

```bash
# Maximum iterations per research loop (1-50, default: 10)
MAX_ITERATIONS=10

# Search timeout in seconds
SEARCH_TIMEOUT=30

# Use graph-based execution for research flows
USE_GRAPH_EXECUTION=false
```

The agent configuration fields:

```80:85:src/utils/config.py
    # Agent Configuration
    max_iterations: int = Field(default=10, ge=1, le=50)
    search_timeout: int = Field(default=30, description="Seconds to wait for search")
    use_graph_execution: bool = Field(
        default=False, description="Use graph-based execution for research flows"
    )
```

### Budget & Rate Limiting Configuration

Control resource limits for research loops:

```bash
# Default token budget per research loop (1000-1000000, default: 100000)
DEFAULT_TOKEN_LIMIT=100000

# Default time limit per research loop in minutes (1-120, default: 10)
DEFAULT_TIME_LIMIT_MINUTES=10

# Default iterations limit per research loop (1-50, default: 10)
DEFAULT_ITERATIONS_LIMIT=10
```

The budget configuration with validation:

```87:105:src/utils/config.py
    # Budget & Rate Limiting Configuration
    default_token_limit: int = Field(
        default=100000,
        ge=1000,
        le=1000000,
        description="Default token budget per research loop",
    )
    default_time_limit_minutes: int = Field(
        default=10,
        ge=1,
        le=120,
        description="Default time limit per research loop (minutes)",
    )
    default_iterations_limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Default iterations limit per research loop",
    )
```

### RAG Service Configuration

Configure the Retrieval-Augmented Generation service:

```bash
# ChromaDB collection name for RAG
RAG_COLLECTION_NAME=deepcritical_evidence

# Number of top results to retrieve from RAG (1-50, default: 5)
RAG_SIMILARITY_TOP_K=5

# Automatically ingest evidence into RAG
RAG_AUTO_INGEST=true
```

The RAG configuration:

```127:141:src/utils/config.py
    # RAG Service Configuration
    rag_collection_name: str = Field(
        default="deepcritical_evidence",
        description="ChromaDB collection name for RAG",
    )
    rag_similarity_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top results to retrieve from RAG",
    )
    rag_auto_ingest: bool = Field(
        default=True,
        description="Automatically ingest evidence into RAG",
    )
```

### ChromaDB Configuration

Configure the vector database for embeddings and RAG:

```bash
# ChromaDB storage path
CHROMA_DB_PATH=./chroma_db

# Whether to persist ChromaDB to disk
CHROMA_DB_PERSIST=true

# ChromaDB server host (for remote ChromaDB, optional)
CHROMA_DB_HOST=localhost

# ChromaDB server port (for remote ChromaDB, optional)
CHROMA_DB_PORT=8000
```

The ChromaDB configuration:

```113:125:src/utils/config.py
    chroma_db_path: str = Field(default="./chroma_db", description="ChromaDB storage path")
    chroma_db_persist: bool = Field(
        default=True,
        description="Whether to persist ChromaDB to disk",
    )
    chroma_db_host: str | None = Field(
        default=None,
        description="ChromaDB server host (for remote ChromaDB)",
    )
    chroma_db_port: int | None = Field(
        default=None,
        description="ChromaDB server port (for remote ChromaDB)",
    )
```

### External Services

#### Modal Configuration

Modal is used for secure sandbox execution of statistical analysis:

```bash
# Modal Token ID (for Modal sandbox execution)
MODAL_TOKEN_ID=your_modal_token_id_here

# Modal Token Secret
MODAL_TOKEN_SECRET=your_modal_token_secret_here
```

The Modal configuration:

```110:112:src/utils/config.py
    # External Services
    modal_token_id: str | None = Field(default=None, description="Modal token ID")
    modal_token_secret: str | None = Field(default=None, description="Modal token secret")
```

### Logging Configuration

Configure structured logging:

```bash
# Log Level: "DEBUG", "INFO", "WARNING", or "ERROR"
LOG_LEVEL=INFO
```

The logging configuration:

```107:108:src/utils/config.py
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
```

Logging is configured via the `configure_logging()` function:

```212:231:src/utils/config.py
def configure_logging(settings: Settings) -> None:
    """Configure structured logging with the configured log level."""
    # Set stdlib logging level from settings
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
```

## Configuration Properties

The `Settings` class provides helpful properties for checking configuration state:

### API Key Availability

Check which API keys are available:

```171:189:src/utils/config.py
    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is available."""
        return bool(self.openai_api_key)

    @property
    def has_anthropic_key(self) -> bool:
        """Check if Anthropic API key is available."""
        return bool(self.anthropic_api_key)

    @property
    def has_huggingface_key(self) -> bool:
        """Check if HuggingFace API key is available."""
        return bool(self.huggingface_api_key or self.hf_token)

    @property
    def has_any_llm_key(self) -> bool:
        """Check if any LLM API key is available."""
        return self.has_openai_key or self.has_anthropic_key or self.has_huggingface_key
```

**Usage:**

```python
from src.utils.config import settings

# Check API key availability
if settings.has_openai_key:
    # Use OpenAI
    pass

if settings.has_anthropic_key:
    # Use Anthropic
    pass

if settings.has_huggingface_key:
    # Use HuggingFace
    pass

if settings.has_any_llm_key:
    # At least one LLM is available
    pass
```

### Service Availability

Check if external services are configured:

```143:146:src/utils/config.py
    @property
    def modal_available(self) -> bool:
        """Check if Modal credentials are configured."""
        return bool(self.modal_token_id and self.modal_token_secret)
```

```191:204:src/utils/config.py
    @property
    def web_search_available(self) -> bool:
        """Check if web search is available (either no-key provider or API key present)."""
        if self.web_search_provider == "duckduckgo":
            return True  # No API key required
        if self.web_search_provider == "serper":
            return bool(self.serper_api_key)
        if self.web_search_provider == "searchxng":
            return bool(self.searchxng_host)
        if self.web_search_provider == "brave":
            return bool(self.brave_api_key)
        if self.web_search_provider == "tavily":
            return bool(self.tavily_api_key)
        return False
```

**Usage:**

```python
from src.utils.config import settings

# Check service availability
if settings.modal_available:
    # Use Modal sandbox
    pass

if settings.web_search_available:
    # Web search is configured
    pass
```

### API Key Retrieval

Get the API key for the configured provider:

```148:160:src/utils/config.py
    def get_api_key(self) -> str:
        """Get the API key for the configured provider."""
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ConfigurationError("OPENAI_API_KEY not set")
            return self.openai_api_key

        if self.llm_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ConfigurationError("ANTHROPIC_API_KEY not set")
            return self.anthropic_api_key

        raise ConfigurationError(f"Unknown LLM provider: {self.llm_provider}")
```

For OpenAI-specific operations (e.g., Magentic mode):

```162:169:src/utils/config.py
    def get_openai_api_key(self) -> str:
        """Get OpenAI API key (required for Magentic function calling)."""
        if not self.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY not set. Magentic mode requires OpenAI for function calling. "
                "Use mode='simple' for other providers."
            )
        return self.openai_api_key
```

## Configuration Usage in Codebase

The configuration system is used throughout the codebase:

### LLM Factory

The LLM factory uses settings to create appropriate models:

```129:144:src/utils/llm_factory.py
    if settings.llm_provider == "huggingface":
        model_name = settings.huggingface_model or "meta-llama/Llama-3.1-8B-Instruct"
        hf_provider = HuggingFaceProvider(api_key=settings.hf_token)
        return HuggingFaceModel(model_name, provider=hf_provider)

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY not set for pydantic-ai")
        provider = OpenAIProvider(api_key=settings.openai_api_key)
        return OpenAIModel(settings.openai_model, provider=provider)

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ConfigurationError("ANTHROPIC_API_KEY not set for pydantic-ai")
        anthropic_provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        return AnthropicModel(settings.anthropic_model, provider=anthropic_provider)
```

### Embedding Service

The embedding service uses local embedding model configuration:

```29:31:src/services/embeddings.py
    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or settings.local_embedding_model
        self._model = SentenceTransformer(self._model_name)
```

### Orchestrator Factory

The orchestrator factory uses settings to determine mode:

```69:80:src/orchestrator_factory.py
def _determine_mode(explicit_mode: str | None) -> str:
    """Determine which mode to use."""
    if explicit_mode:
        if explicit_mode in ("magentic", "advanced"):
            return "advanced"
        return "simple"

    # Auto-detect: advanced if paid API key available
    if settings.has_openai_key:
        return "advanced"

    return "simple"
```

## Environment Variables Reference

### Required (at least one LLM)

- `OPENAI_API_KEY` - OpenAI API key (required for OpenAI provider)
- `ANTHROPIC_API_KEY` - Anthropic API key (required for Anthropic provider)
- `HF_TOKEN` or `HUGGINGFACE_API_KEY` - HuggingFace API token (optional, can work without for public models)

#### LLM Configuration Variables

- `LLM_PROVIDER` - Provider to use: `"openai"`, `"anthropic"`, or `"huggingface"` (default: `"huggingface"`)
- `OPENAI_MODEL` - OpenAI model name (default: `"gpt-5.1"`)
- `ANTHROPIC_MODEL` - Anthropic model name (default: `"claude-sonnet-4-5-20250929"`)
- `HUGGINGFACE_MODEL` - HuggingFace model ID (default: `"meta-llama/Llama-3.1-8B-Instruct"`)

#### Embedding Configuration Variables

- `EMBEDDING_PROVIDER` - Provider: `"openai"`, `"local"`, or `"huggingface"` (default: `"local"`)
- `OPENAI_EMBEDDING_MODEL` - OpenAI embedding model (default: `"text-embedding-3-small"`)
- `LOCAL_EMBEDDING_MODEL` - Local sentence-transformers model (default: `"all-MiniLM-L6-v2"`)
- `HUGGINGFACE_EMBEDDING_MODEL` - HuggingFace embedding model (default: `"sentence-transformers/all-MiniLM-L6-v2"`)

#### Web Search Configuration Variables

- `WEB_SEARCH_PROVIDER` - Provider: `"serper"`, `"searchxng"`, `"brave"`, `"tavily"`, or `"duckduckgo"` (default: `"duckduckgo"`)
- `SERPER_API_KEY` - Serper API key (required for Serper provider)
- `SEARCHXNG_HOST` - SearchXNG host URL (required for SearchXNG provider)
- `BRAVE_API_KEY` - Brave Search API key (required for Brave provider)
- `TAVILY_API_KEY` - Tavily API key (required for Tavily provider)

#### PubMed Configuration Variables

- `NCBI_API_KEY` - NCBI API key (optional, increases rate limit from 3 to 10 req/sec)

#### Agent Configuration Variables

- `MAX_ITERATIONS` - Maximum iterations per research loop (1-50, default: `10`)
- `SEARCH_TIMEOUT` - Search timeout in seconds (default: `30`)
- `USE_GRAPH_EXECUTION` - Use graph-based execution (default: `false`)

#### Budget Configuration Variables

- `DEFAULT_TOKEN_LIMIT` - Default token budget per research loop (1000-1000000, default: `100000`)
- `DEFAULT_TIME_LIMIT_MINUTES` - Default time limit in minutes (1-120, default: `10`)
- `DEFAULT_ITERATIONS_LIMIT` - Default iterations limit (1-50, default: `10`)

#### RAG Configuration Variables

- `RAG_COLLECTION_NAME` - ChromaDB collection name (default: `"deepcritical_evidence"`)
- `RAG_SIMILARITY_TOP_K` - Number of top results to retrieve (1-50, default: `5`)
- `RAG_AUTO_INGEST` - Automatically ingest evidence into RAG (default: `true`)

#### ChromaDB Configuration Variables

- `CHROMA_DB_PATH` - ChromaDB storage path (default: `"./chroma_db"`)
- `CHROMA_DB_PERSIST` - Whether to persist ChromaDB to disk (default: `true`)
- `CHROMA_DB_HOST` - ChromaDB server host (optional, for remote ChromaDB)
- `CHROMA_DB_PORT` - ChromaDB server port (optional, for remote ChromaDB)

#### External Services Variables

- `MODAL_TOKEN_ID` - Modal token ID (optional, for Modal sandbox execution)
- `MODAL_TOKEN_SECRET` - Modal token secret (optional, for Modal sandbox execution)

#### Logging Configuration Variables

- `LOG_LEVEL` - Log level: `"DEBUG"`, `"INFO"`, `"WARNING"`, or `"ERROR"` (default: `"INFO"`)

## Validation

Settings are validated on load using Pydantic validation:

- **Type Checking**: All fields are strongly typed
- **Range Validation**: Numeric fields have min/max constraints (e.g., `ge=1, le=50` for `max_iterations`)
- **Literal Validation**: Enum fields only accept specific values (e.g., `Literal["openai", "anthropic", "huggingface"]`)
- **Required Fields**: API keys are checked when accessed via `get_api_key()` or `get_openai_api_key()`

### Validation Examples

The `max_iterations` field has range validation:

```81:81:src/utils/config.py
    max_iterations: int = Field(default=10, ge=1, le=50)
```

The `llm_provider` field has literal validation:

```26:28:src/utils/config.py
    llm_provider: Literal["openai", "anthropic", "huggingface"] = Field(
        default="openai", description="Which LLM provider to use"
    )
```

## Error Handling

Configuration errors raise `ConfigurationError` from `src/utils/exceptions.py`:

```22:25:src/utils/exceptions.py
class ConfigurationError(DeepCriticalError):
    """Raised when configuration is invalid."""

    pass
```

### Error Handling Example

```python
from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

try:
    api_key = settings.get_api_key()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

### Common Configuration Errors

1. **Missing API Key**: When `get_api_key()` is called but the required API key is not set
2. **Invalid Provider**: When `llm_provider` is set to an unsupported value
3. **Out of Range**: When numeric values exceed their min/max constraints
4. **Invalid Literal**: When enum fields receive unsupported values

## Configuration Best Practices

1. **Use `.env` File**: Store sensitive keys in `.env` file (add to `.gitignore`)
2. **Check Availability**: Use properties like `has_openai_key` before accessing API keys
3. **Handle Errors**: Always catch `ConfigurationError` when calling `get_api_key()`
4. **Validate Early**: Configuration is validated on import, so errors surface immediately
5. **Use Defaults**: Leverage sensible defaults for optional configuration

## Future Enhancements

The following configurations are planned for future phases:

1. **Additional LLM Providers**: DeepSeek, OpenRouter, Gemini, Perplexity, Azure OpenAI, Local models
2. **Model Selection**: Reasoning/main/fast model configuration
3. **Service Integration**: Additional service integrations and configurations
