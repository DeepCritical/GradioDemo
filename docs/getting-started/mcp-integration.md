# MCP Integration

DeepCritical exposes a Model Context Protocol (MCP) server, allowing you to use its search tools directly from Claude Desktop or other MCP clients.

## What is MCP?

The Model Context Protocol (MCP) is a standard for connecting AI assistants to external tools and data sources. DeepCritical implements an MCP server that exposes its search capabilities as MCP tools.

## MCP Server URL

When running locally:

```
http://localhost:7860/gradio_api/mcp/
```

## Claude Desktop Configuration

### 1. Locate Configuration File

**macOS**:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows**:
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux**:
```
~/.config/Claude/claude_desktop_config.json
```

### 2. Add DeepCritical Server

Edit `claude_desktop_config.json` and add:

```json
{
  "mcpServers": {
    "deepcritical": {
      "url": "http://localhost:7860/gradio_api/mcp/"
    }
  }
}
```

### 3. Restart Claude Desktop

Close and restart Claude Desktop for changes to take effect.

### 4. Verify Connection

In Claude Desktop, you should see DeepCritical tools available:
- `search_pubmed`
- `search_clinical_trials`
- `search_biorxiv`
- `search_all`
- `analyze_hypothesis`

## Available Tools

### search_pubmed

Search peer-reviewed biomedical literature from PubMed.

**Parameters**:
- `query` (string): Search query
- `max_results` (integer, optional): Maximum number of results (default: 10)

**Example**:
```
Search PubMed for "metformin diabetes"
```

### search_clinical_trials

Search ClinicalTrials.gov for interventional studies.

**Parameters**:
- `query` (string): Search query
- `max_results` (integer, optional): Maximum number of results (default: 10)

**Example**:
```
Search clinical trials for "Alzheimer's disease treatment"
```

### search_biorxiv

Search bioRxiv/medRxiv preprints via Europe PMC.

**Parameters**:
- `query` (string): Search query
- `max_results` (integer, optional): Maximum number of results (default: 10)

**Example**:
```
Search bioRxiv for "CRISPR gene editing"
```

### search_all

Search all sources simultaneously (PubMed, ClinicalTrials.gov, Europe PMC).

**Parameters**:
- `query` (string): Search query
- `max_results` (integer, optional): Maximum number of results per source (default: 10)

**Example**:
```
Search all sources for "COVID-19 vaccine efficacy"
```

### analyze_hypothesis

Perform secure statistical analysis using Modal sandboxes.

**Parameters**:
- `hypothesis` (string): Hypothesis to analyze
- `data` (string, optional): Data description or code

**Example**:
```
Analyze the hypothesis that metformin reduces cancer risk
```

## Using Tools in Claude Desktop

Once configured, you can ask Claude to use DeepCritical tools:

```
Use DeepCritical to search PubMed for recent papers on Alzheimer's disease treatments.
```

Claude will automatically:
1. Call the appropriate DeepCritical tool
2. Retrieve results
3. Use the results in its response

## Troubleshooting

### Connection Issues

**Server Not Found**:
- Ensure DeepCritical is running (`uv run gradio run src/app.py`)
- Verify the URL in `claude_desktop_config.json` is correct
- Check that port 7860 is not blocked by firewall

**Tools Not Appearing**:
- Restart Claude Desktop after configuration changes
- Check Claude Desktop logs for errors
- Verify MCP server is accessible at the configured URL

### Authentication

If DeepCritical requires authentication:
- Configure API keys in DeepCritical settings
- Use HuggingFace OAuth login
- Ensure API keys are valid

## Advanced Configuration

### Custom Port

If running on a different port, update the URL:

```json
{
  "mcpServers": {
    "deepcritical": {
      "url": "http://localhost:8080/gradio_api/mcp/"
    }
  }
}
```

### Multiple Instances

You can configure multiple DeepCritical instances:

```json
{
  "mcpServers": {
    "deepcritical-local": {
      "url": "http://localhost:7860/gradio_api/mcp/"
    },
    "deepcritical-remote": {
      "url": "https://your-server.com/gradio_api/mcp/"
    }
  }
}
```

## Next Steps

- Learn about [Configuration](../configuration/index.md) for advanced settings
- Explore [Examples](examples.md) for use cases
- Read the [Architecture Documentation](../architecture/graph-orchestration.md)













