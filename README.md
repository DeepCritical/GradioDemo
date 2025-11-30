---
title: The DETERMINATOR
emoji: 🐉
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: "6.0.1"
python_version: "3.11"
app_file: src/app.py
hf_oauth: true
hf_oauth_expiration_minutes: 480
hf_oauth_scopes:
 - inference-api
pinned: true
license: mit
tags:
  - mcp-in-action-track-enterprise
  - mcp-hackathon
  - deep-research
  - biomedical-ai
  - pydantic-ai
  - llamaindex
  - modal
  - building-mcp-track-enterprise
  - building-mcp-track-consumer
  - mcp-in-action-track-enterprise
  - mcp-in-action-track-consumer
  - building-mcp-track-modal
  - building-mcp-track-blaxel
  - building-mcp-track-llama-index
  - building-mcp-track-HUGGINGFACE 
---

> [!IMPORTANT]
> **You are reading the Gradio Demo README!**
> 
> - 📚 **Documentation**: See our [technical documentation](deepcritical.github.io/GradioDemo/) for detailed information
> - 📖 **Complete README**: Check out the [full README](.github/README.md) for setup, configuration, and contribution guidelines
> - 🏆 **Hackathon Submission**: Keep reading below for more information about our MCP Hackathon submission

<div align="center">

[![GitHub](https://img.shields.io/github/stars/DeepCritical/GradioDemo?style=for-the-badge&logo=github&logoColor=white&label=GitHub&labelColor=181717&color=181717)](https://github.com/DeepCritical/GradioDemo)
[![Documentation](https://img.shields.io/badge/Docs-0080FF?style=for-the-badge&logo=readthedocs&logoColor=white&labelColor=0080FF&color=0080FF)](deepcritical.github.io/GradioDemo/)
[![Demo](https://img.shields.io/badge/Demo-FFD21E?style=for-the-badge&logo=huggingface&logoColor=white&labelColor=FFD21E&color=FFD21E)](https://huggingface.co/spaces/DataQuests/DeepCritical)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white&label=Watch%20Demo&labelColor=FF0000&color=FF0000)](https://www.youtube.com/watch?v=https://youtu.be/Mb0M83BqgOw)
[![codecov](https://codecov.io/gh/DeepCritical/GradioDemo/graph/badge.svg?token=B1f05RCGpz)](https://codecov.io/gh/DeepCritical/GradioDemo)
[![Join us on Discord](https://img.shields.io/discord/1109943800132010065?label=Discord&logo=discord&style=flat-square)](https://discord.gg/qdfnvSPcqP) 


</div>

# The DETERMINATOR

## About

The DETERMINATOR is a powerful generalist deep research agent system that stops at nothing until finding precise answers to complex questions. It uses iterative search-and-judge loops to comprehensively investigate any research question from any domain.


> For this hackathon we're proposing a simple yet powerful Deep Research Agent that iteratively looks for the answer until it finds it using general purpose websearch and special purpose retrievers for technical retrievers.

## Who We Are & Motivation

We're a group from the `DeepCritical` Group that met in the `hugging-science` discord.

We're enthusiastic about strongly typed and robust pythonic agentic frameworks , currently building ai-assisted multi-agent systems for research automations , like critical literature reviews , clinical data retrival , and bio informatics and computational medicine applications . 

Starting from Magentic Design Patterns for agentic systems , we discovered we could get better results with iterative graphs , orchestrators and planners with magentic agentics as single tools inside iterations.

## Do You Like This App ? 

Please join us @ https://hf.co/spaces/DataQuests/DeepCritical where we will keep maintaining it !

## The DETERMINATOR is Lightweight and POWERFUL

- very accessible (multimodal inputs , audio and text out)
- fully local embeddings 
- configurable providers (local/hosted) for websearch
- all data stays local
- fully configurable models and huggingface providers with login
- easily extensible and hackable
- uses Gradio a lot (clients, mcp , third party huggingface tools)
- Modal for text-to-speech (remote gpu for "local model")
- Braxel for statistical analysis (code execution sandbox)
- Open Source Models from around the 🌐World
- Using Google Gemma , Qwen , Zai , Llama , Mistral Reasoning Models
- Nebius , Together , Scaleway , Hyperbolic, Novita , nscale ,  Sambanova , ovh , fireworks, all supported and configurable.
- 💖 made with love


## What Can It Do ? 

- long running tasks (potentially millions of tokens over hours and hours)
- data processing and rendering
- statistical analyses 
- literature reviews 
- websearch
- synthetize complex information
- find hard to find information

## Deep Critical In the Media 

- Social Medial Posts about Deep Critical :
  - 𝕏 [![X](https://x.com/marioaderman/status/1995247432444133471)]
  - 💼 [![LinkedIn](https://www.linkedin.com/feed/update/urn:li:activity:7400984658496081920/)]
  - 𝕏 [![X](https://x.com/viratzzs/status/1995258812165664942)]
  
  -💼 [![LinkedIn](https://www.linkedin.com/in/ana-bossler-07304717?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=ios_app)
  -
  -

> [!IMPORTANT]
> **IF YOU ARE A JUDGE**
> 
> This project was produced with passion by a group of volunteers please check out or documentation and readmes and please do keep reading below for our story
>
> - 📚 **Documentation**: See our [technical documentation](https://deepcritical.github.io/GradioDemo/) for detailed information
> - 📖 **Complete README**: Check out the Github [full README](.github/README.md) for setup, configuration, and contribution guidelines
> - 🏆 **Hackathon Submission**: Keep reading below for more information about our MCP Hackathon submission


**Key Features**:
- **Generalist**: Handles queries from any domain (medical, technical, business, scientific, etc.)
- **Automatic Medical Detection**: Automatically determines if medical knowledge sources (PubMed, ClinicalTrials.gov) are needed
- **Multi-Source Search**: Web search, PubMed, ClinicalTrials.gov, Europe PMC, RAG
- **Stops at Nothing**: Only stops at configured limits (budget, time, iterations), otherwise continues until finding precise answers
- **Evidence Synthesis**: Comprehensive reports with proper citations

**Important**: The DETERMINATOR is a research tool that synthesizes evidence. It cannot provide medical advice or answer medical questions directly.

## Important information

- **[readme](.github\README.md)**: configure, deploy , contribute and learn more here.
- **[docs](deepcritical.github.io/GradioDemo/)**: want to know how all this works ? read our detailed technical documentation here.
- **[demo](https://huggingface/spaces/DataQuests/DeepCritical)**: Try our demo on huggingface
- **[team](### Team)**: Join us , or follow us !
- **[video]**: See our demo video

## Future Developments

- [] Apply Deep Research Systems To Generate Short Form Video (up to 5 minutes)
- [] Visualize Pydantic Graphs as Loading Screens in the UI
- [] Improve Data Science with more Complex Graph Agents
- [] Create Deep Critical Drug Reporposing / Discovery Demo
- [] Create Deep Critical Literal Review
- [] Create Deep Critical Hypothesis Generator
- [] Create PyPi Package 

## Completed

- [x] **Multi-Source Search**: PubMed, ClinicalTrials.gov, bioRxiv/medRxiv
- [x] **MCP Integration**: Use our tools from Claude Desktop or any MCP client
- [x] **HuggingFace OAuth**: Sign in with HuggingFace 
- [x] **Modal Sandbox**: Secure execution of AI-generated statistical code
- [x] **LlamaIndex RAG**: Semantic search and evidence synthesis
- [x] **HuggingfaceInference**: 
- [x] **HuggingfaceMCP Custom Config To Use Community Tools**:
- [x] **Strongly Typed Composable Graphs**:
- [x] **Specialized Research Teams of Agents**: 

### Team
- **ZJ**
    - 💼 [LinkedIn](https://www.linkedin.com/in/josephpollack/)
- **Mario Aderman**
    - 🤗 [HuggingFace](https://huggingface.co/SeasonalFall84)
    - 💼 [LinkedIn](https://www.linkedin.com/in/mario-aderman/)
    - 𝕏 [X](https://x.com/marioaderman)
- **Joseph Pollack**
    - 🤗 [HuggingFace](https://huggingface.co/Tonic)
    - 💼 [LinkedIn](https://www.linkedin.com/in/josephpollack/)
    - 𝕏 [X](https://x.com/josephpollack)
- **Virat Chauran**
    - 𝕏 [X](https://x.com/viratzzs/)
    - 💼 [LinkedIn](https://www.linkedin.com/in/viratchauhan/)
    - 🤗 [HuggingFace](https://huggingface.co/ViratChauhan)
- **Anna Bossler**
    -  💼 [LinkedIn](https://www.linkedin.com/in/ana-bossler-07304717)


## Acknowledgements

- [DeepBoner](https://hf.co/spaces/mcp-1st-birthday/deepboner)
- Magentic Paper
- [Huggingface](https://hf.co)
- [Gradio](https://gradio.app)
- [DeepCritical](https://github.com/DeepCritical)
- [Modal](https://modal.com)
- Microsoft
- Pydantic
- Llama-index
- Anthhropic/MCP
- All our Tool Providers


## Links

[![GitHub](https://img.shields.io/github/stars/DeepCritical/GradioDemo?style=for-the-badge&logo=github&logoColor=white&label=GitHub&labelColor=181717&color=181717)](https://github.com/DeepCritical/GradioDemo)
[![Documentation](https://img.shields.io/badge/Docs-0080FF?style=for-the-badge&logo=readthedocs&logoColor=white&labelColor=0080FF&color=0080FF)](deepcritical.github.io/GradioDemo/)
[![Demo](https://img.shields.io/badge/Demo-FFD21E?style=for-the-badge&logo=huggingface&logoColor=white&labelColor=FFD21E&color=FFD21E)](https://huggingface.co/spaces/DataQuests/DeepCritical)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white&label=Watch%20Demo&labelColor=FF0000&color=FF0000)](https://www.youtube.com/watch?v=https://youtu.be/Mb0M83BqgOw)
[![codecov](https://codecov.io/gh/DeepCritical/GradioDemo/graph/badge.svg?token=B1f05RCGpz)](https://codecov.io/gh/DeepCritical/GradioDemo)
[![Join us on Discord](https://img.shields.io/discord/1109943800132010065?label=Discord&logo=discord&style=flat-square)](https://discord.gg/qdfnvSPcqP) 
