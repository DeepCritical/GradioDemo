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

The `Settings` class extends `BaseSettings` from `pydantic_settings` and defines all application configuration:

<!--codeinclude-->
[Settings Class Definition](../src/utils/config.py) start_line:13 end_line:21
<!--/codeinclude-->

### Singleton Instance

A global `settings` instance is available for import:

<!--codeinclude-->
[Singleton Instance](../src/utils/config.py) start_line:234 end_line:235
<!--/codeinclude-->

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

<!--codeinclude-->
[OpenAI Model Configuration](../src/utils/config.py) start_line:29 end_line:29
<!--/codeinclude-->

#### Anthropic Configuration

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

The default model is defined in the `Settings` class:

<!--codeinclude-->
[Anthropic Model Configuration](../src/utils/config.py) start_line:30 end_line:32
<!--/codeinclude-->

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

<!--codeinclude-->
[HuggingFace Token Configuration](../src/utils/config.py) start_line:33 end_line:35
<!--/codeinclude-->

<!--codeinclude-->
[HuggingFace API Key Configuration](../src/utils/config.py) start_line:57 end_line:59
<!--/codeinclude-->

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

<!--codeinclude-->
[Embedding Provider Configuration](../src/utils/config.py) start_line:47 end_line:50
<!--/codeinclude-->

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

<!--codeinclude-->
[Web Search Provider Configuration](../src/utils/config.py) start_line:71 end_line:74
<!--/codeinclude-->

**Note**: DuckDuckGo is the default and requires no API key, making it ideal for development and testing.

### PubMed Configuration

PubMed search supports optional NCBI API key for higher rate limits:

```bash
# NCBI API Key (optional, for higher rate limits: 10 req/sec vs 3 req/sec)
NCBI_API_KEY=your_ncbi_api_key_here
```

The PubMed tool uses this configuration:

<!--codeinclude-->
[PubMed Tool Configuration](../src/tools/pubmed.py) start_line:22 end_line:29
<!--/codeinclude-->

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

<!--codeinclude-->
[Agent Configuration](../src/utils/config.py) start_line:80 end_line:85
<!--/codeinclude-->

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

<!--codeinclude-->
[Budget Configuration](../src/utils/config.py) start_line:87 end_line:105
<!--/codeinclude-->

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

<!--codeinclude-->
[RAG Service Configuration](../src/utils/config.py) start_line:127 end_line:141
<!--/codeinclude-->

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

<!--codeinclude-->
[ChromaDB Configuration](../src/utils/config.py) start_line:113 end_line:125
<!--/codeinclude-->

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

<!--codeinclude-->
[Modal Configuration](../src/utils/config.py) start_line:110 end_line:112
<!--/codeinclude-->

### Logging Configuration

Configure structured logging:

```bash
# Log Level: "DEBUG", "INFO", "WARNING", or "ERROR"
LOG_LEVEL=INFO
```

The logging configuration:

<!--codeinclude-->
[Logging Configuration](../src/utils/config.py) start_line:107 end_line:108
<!--/codeinclude-->

Logging is configured via the `configure_logging()` function:

<!--codeinclude-->
[Configure Logging Function](../src/utils/config.py) start_line:212 end_line:231
<!--/codeinclude-->

## Configuration Properties

The `Settings` class provides helpful properties for checking configuration state:

### API Key Availability

Check which API keys are available:

<!--codeinclude-->
[API Key Availability Properties](../src/utils/config.py) start_line:171 end_line:189
<!--/codeinclude-->

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

<!--codeinclude-->
[Modal Availability Property](../src/utils/config.py) start_line:143 end_line:146
<!--/codeinclude-->

<!--codeinclude-->
[Web Search Availability Property](../src/utils/config.py) start_line:191 end_line:204
<!--/codeinclude-->

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

<!--codeinclude-->
[Get API Key Method](../src/utils/config.py) start_line:148 end_line:160
<!--/codeinclude-->

For OpenAI-specific operations (e.g., Magentic mode):

<!--codeinclude-->
[Get OpenAI API Key Method](../src/utils/config.py) start_line:162 end_line:169
<!--/codeinclude-->

## Configuration Usage in Codebase

The configuration system is used throughout the codebase:

### LLM Factory

The LLM factory uses settings to create appropriate models:

<!--codeinclude-->
[LLM Factory Usage](../src/utils/llm_factory.py) start_line:129 end_line:144
<!--/codeinclude-->

### Embedding Service

The embedding service uses local embedding model configuration:

<!--codeinclude-->
[Embedding Service Usage](../src/services/embeddings.py) start_line:29 end_line:31
<!--/codeinclude-->

### Orchestrator Factory

The orchestrator factory uses settings to determine mode:

<!--codeinclude-->
[Orchestrator Factory Mode Detection](../src/orchestrator_factory.py) start_line:97 end_line:110
<!--/codeinclude-->

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

<!--codeinclude-->
[Max Iterations Validation](../src/utils/config.py) start_line:81 end_line:81
<!--/codeinclude-->

The `llm_provider` field has literal validation:

<!--codeinclude-->
[LLM Provider Literal Validation](../src/utils/config.py) start_line:26 end_line:28
<!--/codeinclude-->

## Error Handling

Configuration errors raise `ConfigurationError` from `src/utils/exceptions.py`:

<!--codeinclude-->
[ConfigurationError Class](../src/utils/exceptions.py) start_line:22 end_line:25
<!--/codeinclude-->

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
