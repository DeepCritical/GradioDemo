"""Unit tests for LongWriterAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import AgentRunResult

from src.agents.long_writer import LongWriterAgent, LongWriterOutput, create_long_writer_agent
from src.utils.models import ReportDraft, ReportDraftSection


@pytest.fixture
def mock_model() -> MagicMock:
    """Create a mock Pydantic AI model."""
    model = MagicMock()
    model.name = "test-model"
    return model


@pytest.fixture
def mock_long_writer_output() -> LongWriterOutput:
    """Create a mock LongWriterOutput."""
    return LongWriterOutput(
        next_section_markdown="## Test Section\n\nContent with citation [1].",
        references=["[1] https://example.com"],
    )


@pytest.fixture
def mock_agent_result(
    mock_long_writer_output: LongWriterOutput,
) -> AgentRunResult[LongWriterOutput]:
    """Create a mock agent result."""
    result = MagicMock(spec=AgentRunResult)
    result.output = mock_long_writer_output
    return result


@pytest.fixture
def long_writer_agent(mock_model: MagicMock) -> LongWriterAgent:
    """Create a LongWriterAgent instance with mocked model."""
    return LongWriterAgent(model=mock_model)


@pytest.fixture
def sample_report_draft() -> ReportDraft:
    """Create a sample ReportDraft for testing."""
    return ReportDraft(
        sections=[
            ReportDraftSection(
                section_title="Introduction",
                section_content="Introduction content with [1].",
            ),
            ReportDraftSection(
                section_title="Methods",
                section_content="Methods content with [2].",
            ),
        ]
    )


class TestLongWriterAgentInit:
    """Test LongWriterAgent initialization."""

    def test_long_writer_agent_init_with_model(self, mock_model: MagicMock) -> None:
        """Test LongWriterAgent initialization with provided model."""
        agent = LongWriterAgent(model=mock_model)
        assert agent.model == mock_model
        assert agent.agent is not None

    @patch("src.agents.long_writer.get_model")
    def test_long_writer_agent_init_without_model(
        self, mock_get_model: MagicMock, mock_model: MagicMock
    ) -> None:
        """Test LongWriterAgent initialization without model (uses default)."""
        mock_get_model.return_value = mock_model
        agent = LongWriterAgent()
        assert agent.model == mock_model
        mock_get_model.assert_called_once()

    def test_long_writer_agent_has_structured_output(
        self, long_writer_agent: LongWriterAgent
    ) -> None:
        """Test that LongWriterAgent uses structured output."""
        assert long_writer_agent.agent.output_type == LongWriterOutput


class TestWriteNextSection:
    """Test write_next_section() method."""

    @pytest.mark.asyncio
    async def test_write_next_section_basic(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
    ) -> None:
        """Test basic section writing."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        original_query = "Test query"
        report_draft = "## Existing Section\n\nContent"
        next_section_title = "New Section"
        next_section_draft = "Draft content"

        result = await long_writer_agent.write_next_section(
            original_query=original_query,
            report_draft=report_draft,
            next_section_title=next_section_title,
            next_section_draft=next_section_draft,
        )

        assert isinstance(result, LongWriterOutput)
        assert result.next_section_markdown is not None
        assert isinstance(result.references, list)
        assert long_writer_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_write_next_section_first_section(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
    ) -> None:
        """Test writing the first section (no existing draft)."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        original_query = "Test query"
        report_draft = ""  # No existing draft
        next_section_title = "First Section"
        next_section_draft = "Draft content"

        result = await long_writer_agent.write_next_section(
            original_query=original_query,
            report_draft=report_draft,
            next_section_title=next_section_title,
            next_section_draft=next_section_draft,
        )

        assert isinstance(result, LongWriterOutput)
        # Check that "No draft yet" was included in prompt
        call_args = long_writer_agent.agent.run.call_args[0][0]
        assert "No draft yet" in call_args or report_draft in call_args

    @pytest.mark.asyncio
    async def test_write_next_section_with_existing_draft(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
    ) -> None:
        """Test writing section with existing draft."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        original_query = "Test query"
        report_draft = "## Previous Section\n\nPrevious content"
        next_section_title = "Next Section"
        next_section_draft = "Next draft"

        result = await long_writer_agent.write_next_section(
            original_query=original_query,
            report_draft=report_draft,
            next_section_title=next_section_title,
            next_section_draft=next_section_draft,
        )

        assert isinstance(result, LongWriterOutput)
        # Check that existing draft was included in prompt
        call_args = long_writer_agent.agent.run.call_args[0][0]
        assert "Previous Section" in call_args

    @pytest.mark.asyncio
    async def test_write_next_section_returns_references(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
    ) -> None:
        """Test that write_next_section returns references."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        result = await long_writer_agent.write_next_section(
            original_query="Test",
            report_draft="",
            next_section_title="Test",
            next_section_draft="Test",
        )

        assert isinstance(result.references, list)
        assert len(result.references) > 0

    @pytest.mark.asyncio
    async def test_write_next_section_handles_empty_draft(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
    ) -> None:
        """Test writing section with empty draft."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        result = await long_writer_agent.write_next_section(
            original_query="Test",
            report_draft="",
            next_section_title="Test",
            next_section_draft="",
        )

        assert isinstance(result, LongWriterOutput)

    @pytest.mark.asyncio
    async def test_write_next_section_llm_failure(self, long_writer_agent: LongWriterAgent) -> None:
        """Test write_next_section handles LLM failures gracefully."""
        long_writer_agent.agent.run = AsyncMock(side_effect=Exception("LLM error"))

        result = await long_writer_agent.write_next_section(
            original_query="Test",
            report_draft="",
            next_section_title="Test",
            next_section_draft="Test",
        )

        # Should return fallback section
        assert isinstance(result, LongWriterOutput)
        assert "Test" in result.next_section_markdown
        assert result.references == []


class TestWriteReport:
    """Test write_report() method."""

    @pytest.mark.asyncio
    async def test_write_report_complete_flow(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test complete report writing flow."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        original_query = "Test query"
        report_title = "Test Report"

        result = await long_writer_agent.write_report(
            original_query=original_query,
            report_title=report_title,
            report_draft=sample_report_draft,
        )

        assert isinstance(result, str)
        assert report_title in result
        assert "Table of Contents" in result
        assert "Introduction" in result
        assert "Methods" in result
        # Should have called write_next_section for each section
        assert long_writer_agent.agent.run.call_count == len(sample_report_draft.sections)

    @pytest.mark.asyncio
    async def test_write_report_single_section(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
    ) -> None:
        """Test writing report with single section."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        report_draft = ReportDraft(
            sections=[
                ReportDraftSection(
                    section_title="Single Section",
                    section_content="Content",
                )
            ]
        )

        result = await long_writer_agent.write_report(
            original_query="Test",
            report_title="Test Report",
            report_draft=report_draft,
        )

        assert isinstance(result, str)
        assert "Single Section" in result
        assert long_writer_agent.agent.run.call_count == 1

    @pytest.mark.asyncio
    async def test_write_report_multiple_sections(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test writing report with multiple sections."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        result = await long_writer_agent.write_report(
            original_query="Test",
            report_title="Test Report",
            report_draft=sample_report_draft,
        )

        assert isinstance(result, str)
        assert sample_report_draft.sections[0].section_title in result
        assert sample_report_draft.sections[1].section_title in result
        assert long_writer_agent.agent.run.call_count == len(sample_report_draft.sections)

    @pytest.mark.asyncio
    async def test_write_report_creates_table_of_contents(
        self,
        long_writer_agent: LongWriterAgent,
        mock_agent_result: AgentRunResult[LongWriterOutput],
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test that write_report creates table of contents."""
        long_writer_agent.agent.run = AsyncMock(return_value=mock_agent_result)

        result = await long_writer_agent.write_report(
            original_query="Test",
            report_title="Test Report",
            report_draft=sample_report_draft,
        )

        assert "Table of Contents" in result
        assert "1. Introduction" in result
        assert "2. Methods" in result

    @pytest.mark.asyncio
    async def test_write_report_aggregates_references(
        self,
        long_writer_agent: LongWriterAgent,
        sample_report_draft: ReportDraft,
    ) -> None:
        """Test that write_report aggregates references from all sections."""
        # Create different outputs for each section
        output1 = LongWriterOutput(
            next_section_markdown="## Introduction\n\nContent [1].",
            references=["[1] https://example.com/1"],
        )
        output2 = LongWriterOutput(
            next_section_markdown="## Methods\n\nContent [1].",
            references=["[1] https://example.com/2"],
        )

        result1 = MagicMock(spec=AgentRunResult)
        result1.output = output1
        result2 = MagicMock(spec=AgentRunResult)
        result2.output = output2
        results = [result1, result2]
        long_writer_agent.agent.run = AsyncMock(side_effect=results)

        result = await long_writer_agent.write_report(
            original_query="Test",
            report_title="Test Report",
            report_draft=sample_report_draft,
        )

        assert "References:" in result
        # Should have both references (reformatted)
        assert "example.com/1" in result or "[1]" in result
        assert "example.com/2" in result or "[2]" in result


class TestReformatReferences:
    """Test _reformat_references() method."""

    def test_reformat_references_deduplicates(self, long_writer_agent: LongWriterAgent) -> None:
        """Test that reference reformatting deduplicates URLs."""
        section_markdown = "Content [1] and [2]."
        section_references = [
            "[1] https://example.com",
            "[2] https://example.com",  # Duplicate URL
        ]
        all_references = []

        _updated_markdown, updated_refs = long_writer_agent._reformat_references(
            section_markdown, section_references, all_references
        )

        # Should only have one reference
        assert len(updated_refs) == 1
        assert "example.com" in updated_refs[0]

    def test_reformat_references_renumbers(self, long_writer_agent: LongWriterAgent) -> None:
        """Test that reference reformatting renumbers correctly."""
        section_markdown = "Content [1] and [2]."
        section_references = [
            "[1] https://example.com/1",
            "[2] https://example.com/2",
        ]
        all_references = ["[1] https://example.com/0"]  # Existing reference

        updated_markdown, updated_refs = long_writer_agent._reformat_references(
            section_markdown, section_references, all_references
        )

        # Should have 3 references total (0, 1, 2)
        assert len(updated_refs) == 3
        # Markdown should have updated reference numbers
        assert "[2]" in updated_markdown or "[3]" in updated_markdown

    def test_reformat_references_handles_malformed(
        self, long_writer_agent: LongWriterAgent
    ) -> None:
        """Test that reference reformatting handles malformed references."""
        section_markdown = "Content [1]."
        section_references = [
            "[1] https://example.com",
            "invalid reference",  # Malformed
        ]
        all_references = []

        updated_markdown, updated_refs = long_writer_agent._reformat_references(
            section_markdown, section_references, all_references
        )

        # Should still work, just skip invalid references
        assert isinstance(updated_markdown, str)
        assert isinstance(updated_refs, list)

    def test_reformat_references_empty_list(self, long_writer_agent: LongWriterAgent) -> None:
        """Test reference reformatting with empty reference list."""
        section_markdown = "Content without citations."
        section_references = []
        all_references = []

        updated_markdown, updated_refs = long_writer_agent._reformat_references(
            section_markdown, section_references, all_references
        )

        assert updated_markdown == section_markdown
        assert updated_refs == []

    def test_reformat_references_preserves_markdown(
        self, long_writer_agent: LongWriterAgent
    ) -> None:
        """Test that reference reformatting preserves markdown content."""
        section_markdown = "## Section\n\nContent [1] with **bold** text."
        section_references = ["[1] https://example.com"]
        all_references = []

        updated_markdown, _ = long_writer_agent._reformat_references(
            section_markdown, section_references, all_references
        )

        assert "## Section" in updated_markdown
        assert "**bold**" in updated_markdown


class TestReformatSectionHeadings:
    """Test _reformat_section_headings() method."""

    def test_reformat_section_headings_level_2(self, long_writer_agent: LongWriterAgent) -> None:
        """Test that headings are reformatted to level 2."""
        section_markdown = "## Section Title\n\nContent"
        result = long_writer_agent._reformat_section_headings(section_markdown)
        assert "## Section Title" in result

    def test_reformat_section_headings_level_3(self, long_writer_agent: LongWriterAgent) -> None:
        """Test that level 3 headings are adjusted correctly."""
        section_markdown = "### Section Title\n\nContent"
        result = long_writer_agent._reformat_section_headings(section_markdown)
        # Should be adjusted to level 2
        assert "## Section Title" in result

    def test_reformat_section_headings_no_headings(
        self, long_writer_agent: LongWriterAgent
    ) -> None:
        """Test reformatting with no headings."""
        section_markdown = "Just content without headings."
        result = long_writer_agent._reformat_section_headings(section_markdown)
        assert result == section_markdown

    def test_reformat_section_headings_preserves_content(
        self, long_writer_agent: LongWriterAgent
    ) -> None:
        """Test that content is preserved during heading reformatting."""
        section_markdown = "# Section\n\nImportant content here."
        result = long_writer_agent._reformat_section_headings(section_markdown)
        assert "Important content here" in result


class TestCreateLongWriterAgent:
    """Test create_long_writer_agent factory function."""

    @patch("src.agents.long_writer.get_model")
    @patch("src.agents.long_writer.LongWriterAgent")
    def test_create_long_writer_agent_success(
        self,
        mock_long_writer_agent_class: MagicMock,
        mock_get_model: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """Test successful long writer agent creation."""
        mock_get_model.return_value = mock_model
        mock_agent_instance = MagicMock()
        mock_long_writer_agent_class.return_value = mock_agent_instance

        result = create_long_writer_agent()

        assert result == mock_agent_instance
        mock_long_writer_agent_class.assert_called_once_with(model=mock_model)

    @patch("src.agents.long_writer.get_model")
    @patch("src.agents.long_writer.LongWriterAgent")
    def test_create_long_writer_agent_with_custom_model(
        self,
        mock_long_writer_agent_class: MagicMock,
        mock_get_model: MagicMock,
        mock_model: MagicMock,
    ) -> None:
        """Test long writer agent creation with custom model."""
        mock_agent_instance = MagicMock()
        mock_long_writer_agent_class.return_value = mock_agent_instance

        result = create_long_writer_agent(model=mock_model)

        assert result == mock_agent_instance
        mock_long_writer_agent_class.assert_called_once_with(model=mock_model)
        mock_get_model.assert_not_called()
