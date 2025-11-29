"""Unit tests for Phase 7: Tool output to Evidence conversion."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.research_flow import IterativeResearchFlow
from src.utils.models import Citation, Evidence, ToolAgentOutput


@pytest.fixture
def mock_agents():
    """Create mock agents for the flow."""
    return {
        "knowledge_gap": AsyncMock(),
        "tool_selector": AsyncMock(),
        "thinking": AsyncMock(),
        "writer": AsyncMock(),
    }


@pytest.fixture
def flow(mock_agents):
    """Create an IterativeResearchFlow with mocked agents."""
    with (
        patch("src.orchestrator.research_flow.create_knowledge_gap_agent") as mock_kg,
        patch("src.orchestrator.research_flow.create_tool_selector_agent") as mock_ts,
        patch("src.orchestrator.research_flow.create_thinking_agent") as mock_thinking,
        patch("src.orchestrator.research_flow.create_writer_agent") as mock_writer,
        patch("src.orchestrator.research_flow.create_judge_handler") as mock_judge_factory,
        patch("src.orchestrator.research_flow.get_workflow_state") as mock_state,
    ):
        mock_kg.return_value = mock_agents["knowledge_gap"]
        mock_ts.return_value = mock_agents["tool_selector"]
        mock_thinking.return_value = mock_agents["thinking"]
        mock_writer.return_value = mock_agents["writer"]
        mock_judge_factory.return_value = MagicMock()

        # Mock workflow state
        mock_state_obj = MagicMock()
        mock_state_obj.evidence = []
        mock_state_obj.add_evidence = MagicMock(return_value=1)
        mock_state.return_value = mock_state_obj

        return IterativeResearchFlow(max_iterations=2, max_time_minutes=5)


@pytest.mark.unit
class TestEvidenceConversion:
    """Tests for converting tool outputs to Evidence objects."""

    def test_convert_pubmed_url_to_evidence(self, flow):
        """Should convert PubMed URLs to Evidence with correct source type."""
        tool_results = {
            "pubmed_search": ToolAgentOutput(
                output="Metformin shows neuroprotective effects...",
                sources=["https://pubmed.ncbi.nlm.nih.gov/12345678/"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert isinstance(evidence, Evidence)
        assert evidence.citation.source == "pubmed"
        assert "pubmed.ncbi.nlm.nih.gov" in evidence.citation.url
        assert "Metformin" in evidence.content

    def test_convert_clinicaltrials_url_to_evidence(self, flow):
        """Should convert ClinicalTrials.gov URLs to Evidence with correct source type."""
        tool_results = {
            "clinical_trials": ToolAgentOutput(
                output="Trial NCT12345678 is investigating...",
                sources=["https://clinicaltrials.gov/ct2/show/NCT12345678"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert evidence.citation.source == "clinicaltrials"
        assert "clinicaltrials.gov" in evidence.citation.url

    def test_convert_europepmc_url_to_evidence(self, flow):
        """Should convert EuropePMC URLs to Evidence with correct source type."""
        tool_results = {
            "europepmc_search": ToolAgentOutput(
                output="Study shows promising results...",
                sources=["https://europepmc.org/article/MED/98765432"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert evidence.citation.source == "europepmc"
        assert "europepmc.org" in evidence.citation.url

    def test_convert_web_url_to_evidence(self, flow):
        """Should convert generic web URLs to Evidence with 'rag' source type (default)."""
        tool_results = {
            "web_search": ToolAgentOutput(
                output="General information about the topic...",
                sources=["https://example.com/article"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert evidence.citation.source == "web"  # Default for unknown web sources
        assert "example.com" in evidence.citation.url

    def test_convert_multiple_sources_to_multiple_evidence(self, flow):
        """Should create one Evidence object per source URL."""
        tool_results = {
            "multi_source": ToolAgentOutput(
                output="Combined findings from multiple sources...",
                sources=[
                    "https://pubmed.ncbi.nlm.nih.gov/11111111/",
                    "https://pubmed.ncbi.nlm.nih.gov/22222222/",
                    "https://example.com/article",
                ],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 3
        assert all(isinstance(e, Evidence) for e in evidence_list)
        assert evidence_list[0].citation.source == "pubmed"
        assert evidence_list[1].citation.source == "pubmed"
        assert evidence_list[2].citation.source == "web"  # Default for unknown web sources

    def test_convert_tool_without_sources(self, flow):
        """Should create Evidence even when tool has no sources."""
        tool_results = {
            "no_sources": ToolAgentOutput(
                output="Some findings without URLs...",
                sources=[],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert isinstance(evidence, Evidence)
        assert evidence.citation.url == "tool://no_sources"  # Code uses tool:// prefix
        assert "Some findings" in evidence.content

    def test_truncate_long_content(self, flow):
        """Should truncate content longer than 1500 characters."""
        long_content = "A" * 2000  # 2000 characters
        tool_results = {
            "long_output": ToolAgentOutput(
                output=long_content,
                sources=["https://example.com/article"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert len(evidence.content) <= 1500 + len("... [truncated]")
        assert "... [truncated]" in evidence.content

    def test_preserve_short_content(self, flow):
        """Should preserve content shorter than 1500 characters."""
        short_content = "Short content here."
        tool_results = {
            "short_output": ToolAgentOutput(
                output=short_content,
                sources=["https://example.com/article"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert evidence.content == short_content
        assert "... [truncated]" not in evidence.content

    def test_convert_multiple_tools(self, flow):
        """Should convert outputs from multiple tools."""
        tool_results = {
            "pubmed_tool": ToolAgentOutput(
                output="PubMed finding",
                sources=["https://pubmed.ncbi.nlm.nih.gov/111/"],
            ),
            "web_tool": ToolAgentOutput(
                output="Web finding",
                sources=["https://example.com"],
            ),
            "clinical_trials_tool": ToolAgentOutput(
                output="Trial finding",
                sources=["https://clinicaltrials.gov/ct2/show/NCT123"],
            ),
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 3
        sources = [e.citation.source for e in evidence_list]
        assert "pubmed" in sources
        assert "web" in sources  # Default for unknown web sources
        assert "clinicaltrials" in sources

    def test_evidence_has_default_relevance(self, flow):
        """Evidence should have default relevance score."""
        tool_results = {
            "test_tool": ToolAgentOutput(
                output="Test content",
                sources=["https://example.com"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert evidence.relevance == 0.5  # Default relevance

    def test_evidence_citation_has_required_fields(self, flow):
        """Evidence citations should have all required fields."""
        tool_results = {
            "test_tool": ToolAgentOutput(
                output="Test content",
                sources=["https://pubmed.ncbi.nlm.nih.gov/12345678/"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        assert len(evidence_list) == 1
        citation = evidence_list[0].citation
        assert isinstance(citation, Citation)
        assert citation.title is not None
        assert citation.url is not None
        assert citation.source is not None
        assert citation.date is not None
        assert isinstance(citation.authors, list)

    def test_rag_tool_detection(self, flow):
        """Should detect RAG tool from key name."""
        tool_results = {
            "rag_search": ToolAgentOutput(
                output="RAG finding",
                sources=["https://example.com"],
            )
        }

        evidence_list = flow._convert_tool_outputs_to_evidence(tool_results)

        # RAG tools without URLs should use internal:// URL
        # But if they have URLs, they should be processed normally
        assert len(evidence_list) == 1
        evidence = evidence_list[0]
        assert isinstance(evidence, Evidence)
