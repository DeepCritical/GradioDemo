"""Shared pytest fixtures for all tests."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.models import Citation, Evidence


@pytest.fixture
def mock_httpx_client(mocker):
    """Mock httpx.AsyncClient for API tests."""
    mock = mocker.patch("httpx.AsyncClient")
    mock.return_value.__aenter__ = AsyncMock(return_value=mock.return_value)
    mock.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_llm_response():
    """Factory fixture for mocking LLM responses."""

    def _mock(content: str):
        return AsyncMock(return_value=content)

    return _mock


@pytest.fixture
def sample_evidence():
    """Sample Evidence objects for testing."""
    return [
        Evidence(
            content="Metformin shows neuroprotective properties in Alzheimer's models...",
            citation=Citation(
                source="pubmed",
                title="Metformin and Alzheimer's Disease: A Systematic Review",
                url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
                date="2024-01-15",
                authors=["Smith J", "Johnson M"],
            ),
            relevance=0.85,
        ),
        Evidence(
            content="Research offers faster path to treatment discovery...",
            citation=Citation(
                source="pubmed",
                title="Research Strategies for Treatment Discovery",
                url="https://example.com/drug-repurposing",
                date="Unknown",
                authors=[],
            ),
            relevance=0.72,
        ),
    ]


# Global timeout for integration tests to prevent hanging
@pytest.fixture(scope="session", autouse=True)
def integration_test_timeout():
    """Set default timeout for integration tests."""
    # This fixture runs automatically for all tests
    # Individual tests can override with asyncio.wait_for
    pass


@pytest.fixture(autouse=True)
def default_to_huggingface(monkeypatch):
    """Ensure tests default to HuggingFace provider unless explicitly overridden.
    
    This prevents tests from requiring OpenAI/Anthropic API keys.
    Tests can override by setting LLM_PROVIDER in their environment or mocking settings.
    """
    # Only set if not already set (allows tests to override)
    if "LLM_PROVIDER" not in os.environ:
        monkeypatch.setenv("LLM_PROVIDER", "huggingface")
    
    # Set a dummy HF_TOKEN if not set (prevents errors, but tests should mock actual API calls)
    if "HF_TOKEN" not in os.environ:
        monkeypatch.setenv("HF_TOKEN", "dummy_token_for_testing")


@pytest.fixture
def mock_hf_model():
    """Create a mock HuggingFace model for testing.
    
    This fixture provides a mock model that can be used in agent tests
    to avoid requiring actual API keys.
    """
    model = MagicMock()
    model.name = "meta-llama/Llama-3.1-8B-Instruct"
    model.model_name = "meta-llama/Llama-3.1-8B-Instruct"
    return model


@pytest.fixture(autouse=True)
def auto_mock_get_model(mock_hf_model, request):
    """Automatically mock get_model() in all agent modules.
    
    This fixture runs automatically for all tests (except OpenAI tests) and
    mocks get_model() where it's imported in each agent module, preventing
    tests from requiring actual API keys.
    
    Tests marked with @pytest.mark.openai will skip this fixture.
    Tests can override by explicitly patching get_model() themselves.
    """
    # Skip auto-mocking for OpenAI tests
    if "openai" in request.keywords:
        return
    
    # Patch get_model in all agent modules where it's imported
    agent_modules = [
        "src.agents.input_parser",
        "src.agents.writer",
        "src.agents.long_writer",
        "src.agents.proofreader",
        "src.agents.knowledge_gap",
        "src.agents.tool_selector",
        "src.agents.thinking",
        "src.agents.hypothesis_agent",
        "src.agents.report_agent",
        "src.agents.judge_agent_llm",
        "src.orchestrator.planner_agent",
        "src.services.statistical_analyzer",
    ]
    
    patches = []
    for module in agent_modules:
        try:
            patches.append(patch(f"{module}.get_model", return_value=mock_hf_model))
        except (ImportError, AttributeError):
            # Module might not exist or get_model might not be imported
            pass
    
    # Start all patches
    for patch_obj in patches:
        patch_obj.start()
    
    yield
    
    # Stop all patches
    for patch_obj in patches:
        patch_obj.stop()