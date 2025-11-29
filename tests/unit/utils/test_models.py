"""Unit tests for data models."""

import pytest

from src.utils.models import ReportSection, ResearchReport


@pytest.mark.unit
class TestResearchReport:
    """Tests for ResearchReport model."""

    def test_references_has_default(self) -> None:
        """ResearchReport should allow creation without references field.

        This is critical because LLMs don't always return the references
        field, and we shouldn't fail validation when it's missing.
        """
        report = ResearchReport(
            title="Test Report",
            executive_summary="A" * 100,  # min_length=100
            research_question="Does drug X help condition Y?",
            methodology=ReportSection(title="Methods", content="We searched..."),
            hypotheses_tested=[{"hypothesis": "test", "supported": True}],
            mechanistic_findings=ReportSection(title="Mechanisms", content="Found..."),
            clinical_findings=ReportSection(title="Clinical", content="Trials show..."),
            drug_candidates=["Drug A"],
            limitations=["Small sample"],
            conclusion="Promising results.",
            sources_searched=["pubmed"],
            total_papers_reviewed=10,
            search_iterations=2,
            confidence_score=0.8,
            # NOTE: references intentionally omitted
        )

        # Should have empty list as default
        assert report.references == []

    def test_references_can_be_provided(self) -> None:
        """ResearchReport should accept references when provided."""
        refs = [{"title": "Paper 1", "url": "https://example.com"}]
        report = ResearchReport(
            title="Test Report",
            executive_summary="A" * 100,
            research_question="Does drug X help condition Y?",
            methodology=ReportSection(title="Methods", content="We searched..."),
            hypotheses_tested=[],
            mechanistic_findings=ReportSection(title="Mechanisms", content="Found..."),
            clinical_findings=ReportSection(title="Clinical", content="Trials show..."),
            drug_candidates=[],
            limitations=[],
            conclusion="Results.",
            confidence_score=0.5,
            references=refs,
        )

        assert report.references == refs
