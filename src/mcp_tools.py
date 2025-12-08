"""MCP tool wrappers for The DETERMINATOR search tools.

These functions expose our search tools via MCP protocol.
Each function follows the MCP tool contract:
- Full type hints
- Google-style docstrings with Args section
- Formatted string returns
"""

from src.tools.clinicaltrials import ClinicalTrialsTool
from src.tools.europepmc import EuropePMCTool
from src.tools.pubmed import PubMedTool

# Singleton instances (avoid recreating on each call)
_pubmed = PubMedTool()
_trials = ClinicalTrialsTool()
_europepmc = EuropePMCTool()


async def search_pubmed(query: str, max_results: int = 10) -> str:
    """Search PubMed for peer-reviewed biomedical literature.

    Searches NCBI PubMed database for scientific papers matching your query.
    Returns titles, authors, abstracts, and citation information.

    Args:
        query: Search query (e.g., "metformin alzheimer", "cancer treatment mechanisms")
        max_results: Maximum results to return (1-50, default 10)

    Returns:
        Formatted search results with paper titles, authors, dates, and abstracts
    """
    max_results = max(1, min(50, max_results))  # Clamp to valid range

    results = await _pubmed.search(query, max_results)

    if not results:
        return f"No PubMed results found for: {query}"

    formatted = [f"## PubMed Results for: {query}\n"]
    for i, evidence in enumerate(results, 1):
        formatted.append(f"### {i}. {evidence.citation.title}")
        formatted.append(f"**Authors**: {', '.join(evidence.citation.authors[:3])}")
        formatted.append(f"**Date**: {evidence.citation.date}")
        formatted.append(f"**URL**: {evidence.citation.url}")
        formatted.append(f"\n{evidence.content}\n")

    return "\n".join(formatted)


async def search_clinical_trials(query: str, max_results: int = 10) -> str:
    """Search ClinicalTrials.gov for clinical trial data.

    Searches the ClinicalTrials.gov database for trials matching your query.
    Returns trial titles, phases, status, conditions, and interventions.

    Args:
        query: Search query (e.g., "metformin alzheimer", "diabetes phase 3")
        max_results: Maximum results to return (1-50, default 10)

    Returns:
        Formatted clinical trial information with NCT IDs, phases, and status
    """
    max_results = max(1, min(50, max_results))

    results = await _trials.search(query, max_results)

    if not results:
        return f"No clinical trials found for: {query}"

    formatted = [f"## Clinical Trials for: {query}\n"]
    for i, evidence in enumerate(results, 1):
        formatted.append(f"### {i}. {evidence.citation.title}")
        formatted.append(f"**URL**: {evidence.citation.url}")
        formatted.append(f"**Date**: {evidence.citation.date}")
        formatted.append(f"\n{evidence.content}\n")

    return "\n".join(formatted)


async def search_europepmc(query: str, max_results: int = 10) -> str:
    """Search Europe PMC for preprints and papers.

    Searches Europe PMC, which includes bioRxiv, medRxiv, and peer-reviewed content.
    Useful for finding cutting-edge preprints and open access papers.

    Args:
        query: Search query (e.g., "metformin neuroprotection", "long covid treatment")
        max_results: Maximum results to return (1-50, default 10)

    Returns:
        Formatted results with titles, authors, and abstracts
    """
    max_results = max(1, min(50, max_results))

    results = await _europepmc.search(query, max_results)

    if not results:
        return f"No Europe PMC results found for: {query}"

    formatted = [f"## Europe PMC Results for: {query}\n"]
    for i, evidence in enumerate(results, 1):
        formatted.append(f"### {i}. {evidence.citation.title}")
        formatted.append(f"**Authors**: {', '.join(evidence.citation.authors[:3])}")
        formatted.append(f"**Date**: {evidence.citation.date}")
        formatted.append(f"**URL**: {evidence.citation.url}")
        formatted.append(f"\n{evidence.content}\n")

    return "\n".join(formatted)


async def search_all_sources(query: str, max_per_source: int = 5) -> str:
    """Search all biomedical sources simultaneously.

    Performs parallel search across PubMed, ClinicalTrials.gov, and Europe PMC.
    This is the most comprehensive search option for deep medical research inquiry.

    Args:
        query: Search query (e.g., "metformin alzheimer", "aspirin cancer prevention")
        max_per_source: Maximum results per source (1-20, default 5)

    Returns:
        Combined results from all sources with source labels
    """
    import asyncio

    max_per_source = max(1, min(20, max_per_source))

    # Run all searches in parallel
    pubmed_task = search_pubmed(query, max_per_source)
    trials_task = search_clinical_trials(query, max_per_source)
    europepmc_task = search_europepmc(query, max_per_source)

    pubmed_results, trials_results, europepmc_results = await asyncio.gather(
        pubmed_task, trials_task, europepmc_task, return_exceptions=True
    )

    formatted = [f"# Comprehensive Search: {query}\n"]

    # Add each result section (handle exceptions gracefully)
    if isinstance(pubmed_results, str):
        formatted.append(pubmed_results)
    else:
        formatted.append(f"## PubMed\n*Error: {pubmed_results}*\n")

    if isinstance(trials_results, str):
        formatted.append(trials_results)
    else:
        formatted.append(f"## Clinical Trials\n*Error: {trials_results}*\n")

    if isinstance(europepmc_results, str):
        formatted.append(europepmc_results)
    else:
        formatted.append(f"## Europe PMC\n*Error: {europepmc_results}*\n")

    return "\n---\n".join(formatted)


async def analyze_hypothesis(
    drug: str,
    condition: str,
    evidence_summary: str,
) -> str:
    """Perform statistical analysis of research hypothesis using Modal.

    Executes AI-generated Python code in a secure Modal sandbox to analyze
    the statistical evidence for a research hypothesis.

    Args:
        drug: The drug being evaluated (e.g., "metformin")
        condition: The target condition (e.g., "Alzheimer's disease")
        evidence_summary: Summary of evidence to analyze

    Returns:
        Analysis result with verdict (SUPPORTED/REFUTED/INCONCLUSIVE) and statistics
    """
    from src.services.statistical_analyzer import get_statistical_analyzer
    from src.utils.config import settings
    from src.utils.models import Citation, Evidence

    if not settings.modal_available:
        return "Error: Modal credentials not configured. Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET."

    # Create evidence from summary
    evidence = [
        Evidence(
            content=evidence_summary,
            citation=Citation(
                source="pubmed",
                title=f"Evidence for {drug} in {condition}",
                url="https://example.com",
                date="2024-01-01",
                authors=["User Provided"],
            ),
            relevance=0.9,
        )
    ]

    analyzer = get_statistical_analyzer()
    result = await analyzer.analyze(
        query=f"Can {drug} treat {condition}?",
        evidence=evidence,
        hypothesis={"drug": drug, "target": "unknown", "pathway": "unknown", "effect": condition},
    )

    return f"""## Statistical Analysis: {drug} for {condition}

### Verdict: **{result.verdict}**
**Confidence**: {result.confidence:.0%}

### Key Findings
{chr(10).join(f"- {f}" for f in result.key_findings) or "- No specific findings extracted"}

### Execution Output
```
{result.execution_output}
```

### Generated Code
```python
{result.code_generated}
```

**Executed in Modal Sandbox** - Isolated, secure, reproducible.
"""


async def extract_text_from_image(
    image_path: str, model: str | None = None, hf_token: str | None = None
) -> str:
    """Extract text from an image using OCR.

    Uses the Multimodal-OCR3 Gradio Space to extract text from images.
    Supports various image formats (PNG, JPG, etc.) and can extract text
    from scanned documents, screenshots, and other image types.

    Args:
        image_path: Path to image file
        model: Optional model selection (default: None, uses API default)

    Returns:
        Extracted text from the image
    """
    from src.services.image_ocr import get_image_ocr_service
    from src.utils.config import settings

    try:
        ocr_service = get_image_ocr_service()
        # Use provided token or fallback to env vars
        token = hf_token or settings.hf_token or settings.huggingface_api_key
        extracted_text = await ocr_service.extract_text(image_path, model=model, hf_token=token)

        if not extracted_text:
            return f"No text found in image: {image_path}"

        return f"## Extracted Text from Image\n\n{extracted_text}"

    except Exception as e:
        return f"Error extracting text from image: {e}"


async def transcribe_audio_file(
    audio_path: str,
    source_lang: str | None = None,
    target_lang: str | None = None,
    hf_token: str | None = None,
) -> str:
    """Transcribe audio file to text using speech-to-text.

    Uses the NVIDIA Canary Gradio Space to transcribe audio files.
    Supports various audio formats (WAV, MP3, etc.) and multiple languages.

    Args:
        audio_path: Path to audio file
        source_lang: Source language (default: "English")
        target_lang: Target language (default: "English")

    Returns:
        Transcribed text from the audio file
    """
    from src.services.stt_gradio import get_stt_service
    from src.utils.config import settings

    try:
        stt_service = get_stt_service()
        # Use provided token or fallback to env vars
        token = hf_token or settings.hf_token or settings.huggingface_api_key
        transcribed_text = await stt_service.transcribe_file(
            audio_path,
            source_lang=source_lang,
            target_lang=target_lang,
            hf_token=token,
        )

        if not transcribed_text:
            return f"No transcription found in audio: {audio_path}"

        return f"## Audio Transcription\n\n{transcribed_text}"

    except Exception as e:
        return f"Error transcribing audio: {e}"
