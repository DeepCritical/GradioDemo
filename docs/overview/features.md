# Features

DeepCritical provides a comprehensive set of features for AI-assisted research:

## Core Features

### Multi-Source Search

- **PubMed**: Search peer-reviewed biomedical literature via NCBI E-utilities
- **ClinicalTrials.gov**: Search interventional clinical trials
- **Europe PMC**: Search preprints and peer-reviewed articles (includes bioRxiv/medRxiv)
- **RAG**: Semantic search within collected evidence using LlamaIndex

### MCP Integration

- **Model Context Protocol**: Expose search tools via MCP server
- **Claude Desktop**: Use DeepCritical tools directly from Claude Desktop
- **MCP Clients**: Compatible with any MCP-compatible client

### Authentication

- **HuggingFace OAuth**: Sign in with HuggingFace account for automatic API token usage
- **Manual API Keys**: Support for OpenAI, Anthropic, and HuggingFace API keys
- **Free Tier Support**: Automatic fallback to HuggingFace Inference API

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
- **Iterative Research**: Single-loop research with search-judge-synthesize cycles
- **Deep Research**: Multi-section parallel research with planning and synthesis
- **Magentic Orchestration**: Multi-agent coordination using Microsoft Agent Framework

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

- **Real-Time Chat**: Interactive chat interface
- **Streaming Updates**: Live progress updates
- **Accordion UI**: Organized display of pending/done operations
- **OAuth Integration**: Seamless HuggingFace authentication

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




















