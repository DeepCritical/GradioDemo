# Features

The DETERMINATOR provides a comprehensive set of features for AI-assisted research:

## Core Features

### Multi-Source Search

- **General Web Search**: Search general knowledge sources for any domain
- **Neo4j Knowledge Graph**: Search structured knowledge graph for papers and disease relationships
- **PubMed**: Search peer-reviewed biomedical literature via NCBI E-utilities (automatically used when medical knowledge needed)
- **ClinicalTrials.gov**: Search interventional clinical trials (automatically used when medical knowledge needed)
- **Europe PMC**: Search preprints and peer-reviewed articles (includes bioRxiv/medRxiv)
- **RAG**: Semantic search within collected evidence using LlamaIndex
- **Automatic Source Selection**: Automatically determines which sources are needed based on query analysis

### MCP Integration

- **Model Context Protocol**: Expose search tools via MCP server
- **Claude Desktop**: Use The DETERMINATOR tools directly from Claude Desktop
- **MCP Clients**: Compatible with any MCP-compatible client

### Authentication

- **REQUIRED**: Authentication is mandatory before using the application
- **HuggingFace OAuth**: Sign in with HuggingFace account for automatic API token usage (recommended)
- **Manual API Keys**: Support for HuggingFace API keys via environment variables (`HF_TOKEN` or `HUGGINGFACE_API_KEY`)
- **Free Tier Support**: Automatic fallback to HuggingFace Inference API (public models) when no API key is available
- **Authentication Check**: The application will display an error message if authentication is not provided

### Secure Code Execution

- **Modal Sandbox**: Secure execution of AI-generated statistical code
- **Isolated Environment**: Network isolation and package version pinning
- **Safe Execution**: Prevents malicious code execution

### Semantic Search & RAG

- **LlamaIndex Integration**: Advanced RAG capabilities
- **Vector Storage**: ChromaDB for embedding storage
- **Semantic Deduplication**: Automatic detection of similar evidence
- **Embedding Service**: Local sentence-transformers (no API key required)

### Orchestration Patterns

- **Graph-Based Execution**: Flexible graph orchestration with conditional routing
- **Parallel Research Loops**: Run multiple research tasks concurrently
- **Iterative Research**: Single-loop research with search-judge-synthesize cycles that continues until precise answers are found
- **Deep Research**: Multi-section parallel research with planning and synthesis
- **Magentic Orchestration**: Multi-agent coordination using Microsoft Agent Framework (alias: "advanced" mode)
- **Stops at Nothing**: Only stops at configured limits (budget, time, iterations), otherwise continues until finding precise answers

**Orchestrator Modes**:
- `simple`: Legacy linear search-judge loop
- `advanced` (or `magentic`): Multi-agent coordination (requires OpenAI API key)
- `iterative`: Knowledge-gap-driven research with single loop
- `deep`: Parallel section-based research with planning
- `auto`: Intelligent mode detection based on query complexity

**Graph Research Modes** (used within graph orchestrator):
- `iterative`: Single research loop pattern
- `deep`: Multi-section parallel research pattern
- `auto`: Auto-detect pattern based on query complexity

**Execution Modes**:
- `use_graph=True`: Graph-based execution with parallel and conditional routing
- `use_graph=False`: Agent chains with sequential execution (backward compatible)

### Real-Time Streaming

- **Event Streaming**: Real-time updates via `AsyncGenerator[AgentEvent]`
- **Progress Tracking**: Monitor research progress with detailed event metadata
- **UI Integration**: Seamless integration with Gradio chat interface

### Budget Management

- **Token Budget**: Track and limit LLM token usage
- **Time Budget**: Enforce time limits per research loop
- **Iteration Budget**: Limit maximum iterations
- **Per-Loop Budgets**: Independent budgets for parallel research loops

### State Management

- **Thread-Safe Isolation**: ContextVar-based state management
- **Evidence Deduplication**: Automatic URL-based deduplication
- **Conversation History**: Track iteration history and agent interactions
- **State Synchronization**: Share evidence across parallel loops

### Multimodal Input & Output

- **Image Input (OCR)**: Upload images and extract text using optical character recognition
- **Audio Input (STT)**: Record or upload audio files and transcribe to text using speech-to-text
- **Audio Output (TTS)**: Generate audio responses with text-to-speech synthesis
- **Configurable Settings**: Enable/disable multimodal features via sidebar settings
- **Voice Selection**: Choose from multiple TTS voices (American English: af_*, am_*)
- **Speech Speed Control**: Adjust TTS speech speed (0.5x to 2.0x)
- **Multimodal Processing Service**: Integrated service for processing images and audio files

## Advanced Features

### Agent System

- **Pydantic AI Agents**: Type-safe agent implementation
- **Structured Output**: Pydantic models for agent responses
- **Agent Factory**: Centralized agent creation with fallback support
- **Specialized Agents**: Knowledge gap, tool selector, writer, proofreader, and more

### Search Tools

- **Rate Limiting**: Built-in rate limiting for external APIs
- **Retry Logic**: Automatic retry with exponential backoff
- **Query Preprocessing**: Automatic query enhancement and synonym expansion
- **Evidence Conversion**: Automatic conversion to structured Evidence objects

### Error Handling

- **Custom Exceptions**: Hierarchical exception system
- **Error Chaining**: Preserve exception context
- **Structured Logging**: Comprehensive logging with structlog
- **Graceful Degradation**: Fallback handlers for missing dependencies

### Configuration

- **Pydantic Settings**: Type-safe configuration management
- **Environment Variables**: Support for `.env` files
- **Validation**: Automatic configuration validation
- **Flexible Providers**: Support for multiple LLM and embedding providers

### Testing

- **Unit Tests**: Comprehensive unit test coverage
- **Integration Tests**: Real API integration tests
- **Mock Support**: Extensive mocking utilities
- **Coverage Reports**: Code coverage tracking

## UI Features

### Gradio Interface

- **Real-Time Chat**: Interactive chat interface with multimodal support
- **Streaming Updates**: Live progress updates
- **Accordion UI**: Organized display of pending/done operations
- **OAuth Integration**: Seamless HuggingFace authentication
- **Multimodal Input**: Support for text, images, and audio input in the same interface
- **Sidebar Settings**: Configuration accordions for research, multimodal, and audio settings

### MCP Server

- **RESTful API**: HTTP-based MCP server
- **Tool Discovery**: Automatic tool registration
- **Request Handling**: Async request processing
- **Error Responses**: Structured error responses

## Development Features

### Code Quality

- **Type Safety**: Full type hints with mypy strict mode
- **Linting**: Ruff for code quality
- **Formatting**: Automatic code formatting
- **Pre-commit Hooks**: Automated quality checks

### Documentation

- **Comprehensive Docs**: Detailed documentation for all components
- **Code Examples**: Extensive code examples
- **Architecture Diagrams**: Visual architecture documentation
- **API Reference**: Complete API documentation

