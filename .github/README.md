
> [!IMPORTANT]
> **You are reading the Github README!**
> 
> - 📚 **Documentation**: See our [technical documentation](https://deepcritical.github.io/GradioDemo/) for detailed information
> - 📖 **Demo README**: Check out the [Demo README](..README.md) for setup, configuration, and contribution guidelines
> - 🏆 **Hackathon Submission**: Keep reading below for more information about our MCP Hackathon submission


<div align="center">

[![GitHub](https://img.shields.io/github/stars/DeepCritical/GradioDemo?style=for-the-badge&logo=github&logoColor=white&label=🐙%20GitHub&labelColor=181717&color=181717)](https://github.com/DeepCritical/GradioDemo)
[![Documentation](https://img.shields.io/badge/Docs-0080FF?style=for-the-badge&logo=readthedocs&logoColor=white&labelColor=0080FF&color=0080FF)](deepcritical.github.io/GradioDemo/)
[![Demo](https://img.shields.io/badge/🚀%20Demo-FFD21E?style=for-the-badge&logo=huggingface&logoColor=white&labelColor=FFD21E&color=FFD21E)](https://huggingface.co/spaces/DataQuests/DeepCritical)
[![codecov](https://codecov.io/gh/DeepCritical/GradioDemo/graph/badge.svg?token=B1f05RCGpz)](https://codecov.io/gh/DeepCritical/GradioDemo)
[![Join us on Discord](https://img.shields.io/discord/1109943800132010065?label=Discord&logo=discord&style=flat-square)](https://discord.gg/qdfnvSPcqP) 

</div>

## Quick Start

### 1. Environment Setup

```bash
# Install uv if you haven't already
pip install uv

# Sync dependencies
uv sync --all-extras
```

### 2. Run the UI

```bash
# Start the Gradio app
gradio run "src/app.py"
```

Open your browser to `http://localhost:7860`.

### 3. Authentication (Optional)

**HuggingFace OAuth Login**:
- Click the "Sign in with HuggingFace" button at the top of the app
- Your HuggingFace API token will be automatically used for AI inference
- No need to manually enter API keys when logged in
- OAuth token is used only for the current session and never stored

### 4. Connect via MCP

This application exposes a Model Context Protocol (MCP) server, allowing you to use its search tools directly from Claude Desktop or other MCP clients.

**MCP Server URL**: `http://localhost:7860/gradio_api/mcp/`

**Claude Desktop Configuration**:
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "deepcritical": {
      "url": "http://localhost:7860/gradio_api/mcp/"
    }
  }
}
```
