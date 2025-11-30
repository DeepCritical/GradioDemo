# Single Command Deploy

Deploy with docker instandly with a single command :

```bash
docker run -it -p 7860:7860 --platform=linux/amd64 \
    -e DB_KEY="YOUR_VALUE_HERE" \
    -e SERP_API="YOUR_VALUE_HERE" \
    -e INFERENCE_API="YOUR_VALUE_HERE" \
    -e MODAL_TOKEN_ID="YOUR_VALUE_HERE" \
    -e MODAL_TOKEN_SECRET="YOUR_VALUE_HERE" \
    -e NCBI_API_KEY="YOUR_VALUE_HERE" \
    -e SERPER_API_KEY="YOUR_VALUE_HERE" \
    -e CHROMA_DB_PATH="./chroma_db" \
    -e CHROMA_DB_HOST="localhost" \
    -e CHROMA_DB_PORT="8000" \
    -e RAG_COLLECTION_NAME="deepcritical_evidence" \
    -e RAG_SIMILARITY_TOP_K="5" \
    -e RAG_AUTO_INGEST="true" \
    -e USE_GRAPH_EXECUTION="false" \
    -e DEFAULT_TOKEN_LIMIT="100000" \
    -e DEFAULT_TIME_LIMIT_MINUTES="10" \
    -e DEFAULT_ITERATIONS_LIMIT="10" \
    -e WEB_SEARCH_PROVIDER="duckduckgo" \
    -e MAX_ITERATIONS="10" \
    -e SEARCH_TIMEOUT="30" \
    -e LOG_LEVEL="DEBUG" \
    -e EMBEDDING_PROVIDER="local" \
    -e OPENAI_EMBEDDING_MODEL="text-embedding-3-small" \
    -e LOCAL_EMBEDDING_MODEL="BAAI/bge-small-en-v1.5" \
    -e HUGGINGFACE_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" \
    -e HF_FALLBACK_MODELS="Qwen/Qwen3-Next-80B-A3B-Thinking,Qwen/Qwen3-Next-80B-A3B-Instruct,meta-llama/Llama-3.3-70B-Instruct,meta-llama/Llama-3.1-8B-Instruct,HuggingFaceH4/zephyr-7b-beta,Qwen/Qwen2-7B-Instruct" \
    -e HUGGINGFACE_MODEL="Qwen/Qwen3-Next-80B-A3B-Thinking" \
    registry.hf.space/dataquests-deepcritical:latest python src/app.py
   ```

## Quick start guide

Get up and running with The DETERMINATOR in minutes.

## Start the Application

```bash
uv run gradio run src/app.py
```

Open your browser to `http://localhost:7860`.

## First Research Query

1. **Enter a Research Question**

   Type your research question in the chat interface, for example:
   - "What are the latest treatments for Alzheimer's disease?"
   - "Review the evidence for metformin in cancer prevention"
   - "What clinical trials are investigating COVID-19 vaccines?"

2. **Submit the Query**

   Click "Submit" or press Enter. The system will:
   - Generate observations about your query
   - Identify knowledge gaps
   - Search multiple sources (PubMed, ClinicalTrials.gov, Europe PMC)
   - Evaluate evidence quality
   - Synthesize findings into a report

3. **Review Results**

   Watch the real-time progress in the chat interface:
   - Search operations and results
   - Evidence evaluation
   - Report generation
   - Final research report with citations

## Authentication

### HuggingFace OAuth (Recommended)

1. Click "Sign in with HuggingFace" at the top of the app
2. Authorize the application
3. Your HuggingFace API token will be automatically used
4. No need to manually enter API keys

### Manual API Key

1. Open the Settings accordion
2. Enter your API key:
   - OpenAI API key
   - Anthropic API key
   - HuggingFace API key
3. Click "Save Settings"
4. Manual keys take priority over OAuth tokens

## Understanding the Interface

### Chat Interface

- **Input**: Enter your research questions here
- **Messages**: View conversation history and research progress
- **Streaming**: Real-time updates as research progresses

### Status Indicators

- **Searching**: Active search operations
- **Evaluating**: Evidence quality assessment
- **Synthesizing**: Report generation
- **Complete**: Research finished

### Settings

- **API Keys**: Configure LLM providers
- **Research Mode**: Choose iterative or deep research
- **Budget Limits**: Set token, time, and iteration limits

## Example Queries

### Simple Query

```
What are the side effects of metformin?
```

### Complex Query

```
Review the evidence for using metformin as an anti-aging intervention, 
including clinical trials, mechanisms of action, and safety profile.
```

### Clinical Trial Query

```
What are the active clinical trials investigating Alzheimer's disease treatments?
```

## Next Steps

- Learn about [MCP Integration](mcp-integration.md) to use The DETERMINATOR from Claude Desktop
- Explore [Examples](examples.md) for more use cases
- Read the [Configuration Guide](../configuration/index.md) for advanced settings
- Check out the [Architecture Documentation](../architecture/graph_orchestration.md) to understand how it works















<<<<<<< Updated upstream





=======
>>>>>>> Stashed changes
