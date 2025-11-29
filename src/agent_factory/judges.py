"""Judge handler for evidence assessment using PydanticAI."""

import asyncio
import json
import os
from typing import Any

import structlog
from huggingface_hub import InferenceClient
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel  # type: ignore[attr-defined]
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Try to import AnthropicModel (may not be available if anthropic package is missing)
try:
    from pydantic_ai.models.anthropic import AnthropicModel

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    AnthropicModel = None  # type: ignore[assignment, misc]
    _ANTHROPIC_AVAILABLE = False

# Try to import HuggingFace support (may not be available in all pydantic-ai versions)
# According to https://ai.pydantic.dev/models/huggingface/, HuggingFace support requires
# pydantic-ai with huggingface extra or pydantic-ai-slim[huggingface]
# There are two ways to use HuggingFace:
# 1. Inference API: HuggingFaceModel with HuggingFaceProvider (uses AsyncInferenceClient internally)
# 2. Local models: Would use transformers directly (not via pydantic-ai)
try:
    from huggingface_hub import AsyncInferenceClient
    from pydantic_ai.models.huggingface import HuggingFaceModel
    from pydantic_ai.providers.huggingface import HuggingFaceProvider

    _HUGGINGFACE_AVAILABLE = True
except ImportError:
    HuggingFaceModel = None  # type: ignore[assignment, misc]
    HuggingFaceProvider = None  # type: ignore[assignment, misc]
    AsyncInferenceClient = None  # type: ignore[assignment, misc]
    _HUGGINGFACE_AVAILABLE = False

from src.prompts.judge import (
    SYSTEM_PROMPT,
    format_empty_evidence_prompt,
    format_user_prompt,
)
from src.utils.config import settings
from src.utils.models import AssessmentDetails, Evidence, JudgeAssessment

logger = structlog.get_logger()


def get_model() -> Any:
    """Get the LLM model based on configuration.

    Explicitly passes API keys from settings to avoid requiring
    users to export environment variables manually.
    
    Falls back to HuggingFace if the configured provider's API key is missing,
    which is important for CI/testing environments.
    """
    llm_provider = settings.llm_provider

    if llm_provider == "anthropic":
        if not _ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic not available, falling back to HuggingFace")
        elif settings.anthropic_api_key:
            return AnthropicModel(settings.anthropic_model, api_key=settings.anthropic_api_key)  # type: ignore[call-arg]
        else:
            logger.warning("ANTHROPIC_API_KEY not set, falling back to HuggingFace")

    if llm_provider == "openai":
        if settings.openai_api_key:
            return OpenAIModel(settings.openai_model, api_key=settings.openai_api_key)  # type: ignore[call-overload]
        else:
            logger.warning("OPENAI_API_KEY not set, falling back to HuggingFace")

    if llm_provider == "huggingface":
        if not _HUGGINGFACE_AVAILABLE:
            raise ImportError(
                "HuggingFace models are not available in this version of pydantic-ai. "
                "Please install with: uv add 'pydantic-ai[huggingface]' or use 'openai'/'anthropic' as the LLM provider."
            )
        # Inference API - uses HuggingFace Inference API via AsyncInferenceClient
        # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
        model_name = settings.huggingface_model or "Qwen/Qwen3-Next-80B-A3B-Thinking"
        # Create AsyncInferenceClient for inference API
        hf_client = AsyncInferenceClient(api_key=settings.hf_token)  # type: ignore[misc]
        # Pass client to HuggingFaceProvider for inference API usage
        provider = HuggingFaceProvider(hf_client=hf_client)  # type: ignore[misc]
        return HuggingFaceModel(model_name, provider=provider)  # type: ignore[misc]

    # Default to HuggingFace if provider is unknown or not specified, or if API key is missing
    if llm_provider != "huggingface":
        logger.warning("Unknown LLM provider or missing API key, defaulting to HuggingFace", provider=llm_provider)

    if not _HUGGINGFACE_AVAILABLE:
        raise ImportError(
            "HuggingFace models are not available in this version of pydantic-ai. "
            "Please install with: uv add 'pydantic-ai[huggingface]' or set LLM_PROVIDER to 'openai'/'anthropic'."
        )
    # Inference API - uses HuggingFace Inference API via AsyncInferenceClient
    # Per https://ai.pydantic.dev/models/huggingface/#configure-the-provider
    model_name = settings.huggingface_model or "Qwen/Qwen3-Next-80B-A3B-Thinking"
    # Create AsyncInferenceClient for inference API
    hf_client = AsyncInferenceClient(api_key=settings.hf_token)  # type: ignore[misc]
    # Pass client to HuggingFaceProvider for inference API usage
    provider = HuggingFaceProvider(hf_client=hf_client)  # type: ignore[misc]
    return HuggingFaceModel(model_name, provider=provider)  # type: ignore[misc]


class JudgeHandler:
    """
    Handles evidence assessment using an LLM with structured output.

    Uses PydanticAI to ensure responses match the JudgeAssessment schema.
    """

    def __init__(self, model: Any = None) -> None:
        """
        Initialize the JudgeHandler.

        Args:
            model: Optional PydanticAI model. If None, uses config default.
        """
        self.model = model or get_model()
        self.agent = Agent(  # type: ignore[call-overload]
            model=self.model,
            output_type=JudgeAssessment,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

    async def assess(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> JudgeAssessment:
        """
        Assess evidence and determine if it's sufficient.

        Args:
            question: The user's research question
            evidence: List of Evidence objects from search

        Returns:
            JudgeAssessment with evaluation results

        Raises:
            JudgeError: If assessment fails after retries
        """
        logger.info(
            "Starting evidence assessment",
            question=question[:100],
            evidence_count=len(evidence),
        )

        # Format the prompt based on whether we have evidence
        if evidence:
            user_prompt = format_user_prompt(question, evidence)
        else:
            user_prompt = format_empty_evidence_prompt(question)

        try:
            # Run the agent with structured output
            result = await self.agent.run(user_prompt)
            assessment = result.data

            logger.info(
                "Assessment complete",
                sufficient=assessment.sufficient,
                recommendation=assessment.recommendation,
                confidence=assessment.confidence,
            )

            return assessment  # type: ignore[no-any-return]

        except Exception as e:
            logger.error("Assessment failed", error=str(e))
            # Return a safe default assessment on failure
            return self._create_fallback_assessment(question, str(e))

    def _create_fallback_assessment(
        self,
        question: str,
        error: str,
    ) -> JudgeAssessment:
        """
        Create a fallback assessment when LLM fails.

        Args:
            question: The original question
            error: The error message

        Returns:
            Safe fallback JudgeAssessment
        """
        return JudgeAssessment(
            details=AssessmentDetails(
                mechanism_score=0,
                mechanism_reasoning="Assessment failed due to LLM error",
                clinical_evidence_score=0,
                clinical_reasoning="Assessment failed due to LLM error",
                drug_candidates=[],
                key_findings=[],
            ),
            sufficient=False,
            confidence=0.0,
            recommendation="continue",
            next_search_queries=[
                f"{question} mechanism",
                f"{question} clinical trials",
                f"{question} drug candidates",
            ],
            reasoning=f"Assessment failed: {error}. Recommend retrying with refined queries.",
        )


class HFInferenceJudgeHandler:
    """
    JudgeHandler using HuggingFace Inference API for FREE LLM calls.

    Models are loaded from environment variable HF_FALLBACK_MODELS (comma-separated)
    or use defaults based on currently available inference providers:
    - meta-llama/Llama-3.1-8B-Instruct (gated, multiple providers)
    - HuggingFaceH4/zephyr-7b-beta (ungated, featherless-ai)
    - Qwen/Qwen2-7B-Instruct (ungated, featherless-ai)
    - google/gemma-2-2b-it (gated, nebius)
    """

    @classmethod
    def _get_fallback_models(cls) -> list[str]:
        """Get fallback models from env var or use defaults."""
        from src.utils.config import settings

        # Get from env var or settings
        models_str = os.getenv("HF_FALLBACK_MODELS") or settings.huggingface_fallback_models

        # Parse comma-separated list
        models = [m.strip() for m in models_str.split(",") if m.strip()]

        # Default fallback if empty
        if not models:
            models = [
                "meta-llama/Llama-3.1-8B-Instruct",  # Primary (Gated, multiple providers)
                "HuggingFaceH4/zephyr-7b-beta",  # Fallback (Ungated, featherless-ai)
                "Qwen/Qwen2-7B-Instruct",  # Fallback (Ungated, featherless-ai)
                "google/gemma-2-2b-it",  # Fallback (Gated, nebius)
            ]

        return models

    def __init__(
        self,
        model_id: str | None = None,
        api_key: str | None = None,
        provider: str | None = None,
    ) -> None:
        """
        Initialize with HF Inference client.

        Args:
            model_id: Optional specific model ID. If None, uses FALLBACK_MODELS chain.
            api_key: Optional HuggingFace API key (OAuth token or HF_TOKEN).
                     If provided, will use authenticated access for gated models.
            provider: Optional inference provider name (e.g., "novita", "nebius").
                     If provided, will use that specific provider.
        """
        self.model_id = model_id
        self.api_key = api_key
        self.provider = provider
        # Create InferenceClient without provider - provider will be specified per request
        # Provider should be specified per API call, not at client initialization
        self.client = InferenceClient(token=api_key) if api_key else InferenceClient()
        self.call_count = 0
        self.last_question: str | None = None
        self.last_evidence: list[Evidence] | None = None

    async def assess(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> JudgeAssessment:
        """
        Assess evidence using HuggingFace Inference API.
        Attempts models in order until one succeeds.
        """
        self.call_count += 1
        self.last_question = question
        self.last_evidence = evidence

        # Format the user prompt
        if evidence:
            user_prompt = format_user_prompt(question, evidence)
        else:
            user_prompt = format_empty_evidence_prompt(question)

        models_to_try: list[str] = [self.model_id] if self.model_id else self._get_fallback_models()
        last_error: Exception | None = None

        for model in models_to_try:
            try:
                return await self._call_with_retry(model, user_prompt, question)
            except Exception as e:
                logger.warning("Model failed", model=model, error=str(e))
                last_error = e
                continue

        # All models failed
        logger.error("All HF models failed", error=str(last_error))
        return self._create_fallback_assessment(question, str(last_error))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _call_with_retry(self, model: str, prompt: str, question: str) -> JudgeAssessment:
        """Make API call with retry logic using chat_completion."""
        loop = asyncio.get_running_loop()

        # Build messages for chat_completion (model-agnostic)
        messages = [
            {
                "role": "system",
                "content": f"""{SYSTEM_PROMPT}

IMPORTANT: Respond with ONLY valid JSON matching this schema:
{{
    "details": {{
        "mechanism_score": <int 0-10>,
        "mechanism_reasoning": "<string>",
        "clinical_evidence_score": <int 0-10>,
        "clinical_reasoning": "<string>",
        "drug_candidates": ["<string>", ...],
        "key_findings": ["<string>", ...]
    }},
    "sufficient": <bool>,
    "confidence": <float 0-1>,
    "recommendation": "continue" | "synthesize",
    "next_search_queries": ["<string>", ...],
    "reasoning": "<string>"
}}""",
            },
            {"role": "user", "content": prompt},
        ]

        # Use chat_completion (conversational task - supported by all models)
        # Try multiple approaches to handle provider specification
        # Some models/providers don't work together, so we need fallbacks
        
        attempts = []
        
        # Attempt 1: If provider specified, try model:provider format
        if self.provider:
            attempts.append({
                "model": f"{model}:{self.provider}",
                "description": f"{model} with {self.provider} provider",
            })
        
        # Attempt 2: Try model without provider (let HF auto-select)
        attempts.append({
            "model": model,
            "description": f"{model} (auto provider)",
        })
        
        last_error: Exception | None = None
        for attempt in attempts:
            try:
                call_kwargs = {
                    "messages": messages,
                    "model": attempt["model"],
                    "max_tokens": 1024,
                    "temperature": 0.1,
                }
                
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat_completion(**call_kwargs),  # type: ignore[call-overload]
                )
                # If we get here, the call succeeded
                break
            except Exception as e:
                error_str = str(e)
                # Check if it's a 422 or provider-related error
                if "422" in error_str or "Unprocessable" in error_str:
                    logger.debug(
                        "Provider/model combination failed, trying next approach",
                        attempt=attempt["description"],
                        error=error_str[:100],
                    )
                    last_error = e
                    continue
                # For other errors, re-raise immediately
                raise
        else:
            # All attempts failed
            if last_error:
                raise last_error
            raise ValueError("All model/provider attempts failed")

        # Extract content from response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from model")

        # Extract and parse JSON
        json_data = self._extract_json(content)
        if not json_data:
            raise ValueError("No valid JSON found in response")

        return JudgeAssessment(**json_data)

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        """
        Robust JSON extraction that handles markdown blocks and nested braces.
        """
        text = text.strip()

        # Remove markdown code blocks if present (with bounds checking)
        if "```json" in text:
            parts = text.split("```json", 1)
            if len(parts) > 1:
                inner_parts = parts[1].split("```", 1)
                text = inner_parts[0]
        elif "```" in text:
            parts = text.split("```", 1)
            if len(parts) > 1:
                inner_parts = parts[1].split("```", 1)
                text = inner_parts[0]

        text = text.strip()

        # Find first '{'
        start_idx = text.find("{")
        if start_idx == -1:
            return None

        # Stack-based parsing ignoring chars in strings
        count = 0
        in_string = False
        escape = False

        for i, char in enumerate(text[start_idx:], start=start_idx):
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                count += 1
            elif char == "}":
                count -= 1
                if count == 0:
                    try:
                        result = json.loads(text[start_idx : i + 1])
                        if isinstance(result, dict):
                            return result
                        return None
                    except json.JSONDecodeError:
                        return None

        return None

    def _create_fallback_assessment(
        self,
        question: str,
        error: str,
    ) -> JudgeAssessment:
        """Create a fallback assessment when inference fails."""
        return JudgeAssessment(
            details=AssessmentDetails(
                mechanism_score=0,
                mechanism_reasoning=f"Assessment failed: {error}",
                clinical_evidence_score=0,
                clinical_reasoning=f"Assessment failed: {error}",
                drug_candidates=[],
                key_findings=[],
            ),
            sufficient=False,
            confidence=0.0,
            recommendation="continue",
            next_search_queries=[
                f"{question} mechanism",
                f"{question} clinical trials",
                f"{question} drug candidates",
            ],
            reasoning=f"HF Inference failed: {error}. Recommend configuring OpenAI/Anthropic key.",
        )


def create_judge_handler() -> JudgeHandler:
    """Create a judge handler based on configuration.

    Returns:
        Configured JudgeHandler instance
    """
    return JudgeHandler()


class MockJudgeHandler:
    """
    Mock JudgeHandler for demo mode without LLM calls.

    Extracts meaningful information from real search results
    to provide a useful demo experience without requiring API keys.
    """

    def __init__(self, mock_response: JudgeAssessment | None = None) -> None:
        """
        Initialize with optional mock response.

        Args:
            mock_response: The assessment to return. If None, extracts from evidence.
        """
        self.mock_response = mock_response
        self.call_count = 0
        self.last_question: str | None = None
        self.last_evidence: list[Evidence] | None = None

    def _extract_key_findings(self, evidence: list[Evidence], max_findings: int = 5) -> list[str]:
        """Extract key findings from evidence titles."""
        findings = []
        for e in evidence[:max_findings]:
            # Use first 150 chars of title as a finding
            title = e.citation.title
            if len(title) > 150:
                title = title[:147] + "..."
            findings.append(title)
        return findings if findings else ["No specific findings extracted (demo mode)"]

    def _extract_drug_candidates(self, question: str, evidence: list[Evidence]) -> list[str]:
        """Extract drug candidates - demo mode returns honest message."""
        # Don't attempt heuristic extraction - it produces garbage like "Oral", "Kidney"
        # Real drug extraction requires LLM analysis
        return [
            "Drug identification requires AI analysis",
            "Enter API key above for full results",
        ]

    async def assess(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> JudgeAssessment:
        """Return assessment based on actual evidence (demo mode)."""
        self.call_count += 1
        self.last_question = question
        self.last_evidence = evidence

        if self.mock_response:
            return self.mock_response

        min_evidence = 3
        evidence_count = len(evidence)

        # Extract meaningful data from actual evidence
        drug_candidates = self._extract_drug_candidates(question, evidence)
        key_findings = self._extract_key_findings(evidence)

        # Calculate scores based on evidence quantity
        mechanism_score = min(10, evidence_count * 2) if evidence_count > 0 else 0
        clinical_score = min(10, evidence_count) if evidence_count > 0 else 0

        return JudgeAssessment(
            details=AssessmentDetails(
                mechanism_score=mechanism_score,
                mechanism_reasoning=(
                    f"Demo mode: Found {evidence_count} sources. "
                    "Configure LLM API key for detailed mechanism analysis."
                ),
                clinical_evidence_score=clinical_score,
                clinical_reasoning=(
                    f"Demo mode: {evidence_count} sources retrieved from PubMed, "
                    "ClinicalTrials.gov, and Europe PMC. Full analysis requires LLM API key."
                ),
                drug_candidates=drug_candidates,
                key_findings=key_findings,
            ),
            sufficient=evidence_count >= min_evidence,
            confidence=min(0.5, evidence_count * 0.1) if evidence_count > 0 else 0.0,
            recommendation="synthesize" if evidence_count >= min_evidence else "continue",
            next_search_queries=(
                [f"{question} mechanism", f"{question} clinical trials"]
                if evidence_count < min_evidence
                else []
            ),
            reasoning=(
                f"Demo mode assessment based on {evidence_count} real search results. "
                "For AI-powered analysis with drug candidate identification and "
                "evidence synthesis, configure OPENAI_API_KEY or ANTHROPIC_API_KEY."
            ),
        )
