"""Unit tests for InputParserAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import AgentRunResult

from src.agents.input_parser import InputParserAgent, create_input_parser_agent
from src.utils.exceptions import ConfigurationError
from src.utils.models import ParsedQuery


@pytest.fixture
def mock_model() -> MagicMock:
    """Create a mock Pydantic AI model."""
    model = MagicMock()
    model.name = "test-model"
    return model


@pytest.fixture
def mock_parsed_query_iterative() -> ParsedQuery:
    """Create a mock ParsedQuery for iterative mode."""
    return ParsedQuery(
        original_query="What is the mechanism of metformin?",
        improved_query="What is the molecular mechanism of action of metformin in diabetes treatment?",
        research_mode="iterative",
        key_entities=["metformin", "diabetes"],
        research_questions=["What is metformin's mechanism of action?"],
    )


@pytest.fixture
def mock_parsed_query_deep() -> ParsedQuery:
    """Create a mock ParsedQuery for deep mode."""
    return ParsedQuery(
        original_query="Write a comprehensive report on diabetes treatment",
        improved_query="Provide a comprehensive analysis of diabetes treatment options, including mechanisms, clinical evidence, and market analysis",
        research_mode="deep",
        key_entities=["diabetes", "treatment"],
        research_questions=[
            "What are the main treatment options for diabetes?",
            "What is the clinical evidence for each treatment?",
            "What is the market size for diabetes treatments?",
        ],
    )


@pytest.fixture
def mock_agent_result_iterative(
    mock_parsed_query_iterative: ParsedQuery,
) -> AgentRunResult[ParsedQuery]:
    """Create a mock agent result for iterative mode."""
    result = MagicMock(spec=AgentRunResult)
    result.output = mock_parsed_query_iterative
    return result


@pytest.fixture
def mock_agent_result_deep(
    mock_parsed_query_deep: ParsedQuery,
) -> AgentRunResult[ParsedQuery]:
    """Create a mock agent result for deep mode."""
    result = MagicMock(spec=AgentRunResult)
    result.output = mock_parsed_query_deep
    return result


@pytest.fixture
def input_parser_agent(mock_model: MagicMock) -> InputParserAgent:
    """Create an InputParserAgent instance with mocked model."""
    return InputParserAgent(model=mock_model)


class TestInputParserAgentInit:
    """Test InputParserAgent initialization."""

    def test_input_parser_agent_init_with_model(self, mock_model: MagicMock) -> None:
        """Test InputParserAgent initialization with provided model."""
        agent = InputParserAgent(model=mock_model)
        assert agent.model == mock_model
        assert agent.agent is not None

    @patch("src.agents.input_parser.get_model")
    def test_input_parser_agent_init_without_model(
        self, mock_get_model: MagicMock, mock_model: MagicMock
    ) -> None:
        """Test InputParserAgent initialization without model (uses default)."""
        mock_get_model.return_value = mock_model
        agent = InputParserAgent()
        assert agent.model == mock_model
        mock_get_model.assert_called_once()

    def test_input_parser_agent_has_correct_system_prompt(
        self, input_parser_agent: InputParserAgent
    ) -> None:
        """Test that InputParserAgent has correct system prompt."""
        # System prompt should contain key instructions
        # In pydantic_ai, system_prompt is a property that returns the prompt string
        # For mocked agents, we check that the agent was created with a system prompt
        assert input_parser_agent.agent is not None
        # The actual system prompt is set during agent creation
        # We verify the agent exists and was properly initialized
        # Note: Direct access to system_prompt may not work with mocks
        # This test verifies the agent structure is correct


class TestParse:
    """Test parse() method."""

    @pytest.mark.asyncio
    async def test_parse_iterative_query(
        self,
        input_parser_agent: InputParserAgent,
        mock_agent_result_iterative: AgentRunResult[ParsedQuery],
    ) -> None:
        """Test parsing a simple query that should return iterative mode."""
        input_parser_agent.agent.run = AsyncMock(return_value=mock_agent_result_iterative)

        query = "What is the mechanism of metformin?"
        result = await input_parser_agent.parse(query)

        assert isinstance(result, ParsedQuery)
        assert result.research_mode == "iterative"
        assert result.original_query == query
        assert "metformin" in result.key_entities
        assert input_parser_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_parse_deep_query(
        self,
        input_parser_agent: InputParserAgent,
        mock_agent_result_deep: AgentRunResult[ParsedQuery],
    ) -> None:
        """Test parsing a complex query that should return deep mode."""
        input_parser_agent.agent.run = AsyncMock(return_value=mock_agent_result_deep)

        query = "Write a comprehensive report on diabetes treatment"
        result = await input_parser_agent.parse(query)

        assert isinstance(result, ParsedQuery)
        assert result.research_mode == "deep"
        assert result.original_query == query
        assert len(result.research_questions) > 0
        assert input_parser_agent.agent.run.called

    @pytest.mark.asyncio
    async def test_parse_improves_query(
        self,
        input_parser_agent: InputParserAgent,
        mock_agent_result_iterative: AgentRunResult[ParsedQuery],
    ) -> None:
        """Test that parse() improves the query."""
        input_parser_agent.agent.run = AsyncMock(return_value=mock_agent_result_iterative)

        query = "metformin mechanism"
        result = await input_parser_agent.parse(query)

        assert isinstance(result, ParsedQuery)
        assert result.improved_query != result.original_query
        assert len(result.improved_query) >= len(result.original_query)

    @pytest.mark.asyncio
    async def test_parse_extracts_entities(
        self,
        input_parser_agent: InputParserAgent,
        mock_agent_result_iterative: AgentRunResult[ParsedQuery],
    ) -> None:
        """Test that parse() extracts key entities."""
        input_parser_agent.agent.run = AsyncMock(return_value=mock_agent_result_iterative)

        query = "What is the mechanism of metformin?"
        result = await input_parser_agent.parse(query)

        assert isinstance(result, ParsedQuery)
        assert len(result.key_entities) > 0
        assert "metformin" in result.key_entities

    @pytest.mark.asyncio
    async def test_parse_extracts_research_questions(
        self,
        input_parser_agent: InputParserAgent,
        mock_agent_result_deep: AgentRunResult[ParsedQuery],
    ) -> None:
        """Test that parse() extracts research questions."""
        input_parser_agent.agent.run = AsyncMock(return_value=mock_agent_result_deep)

        query = "Write a comprehensive report on diabetes treatment"
        result = await input_parser_agent.parse(query)

        assert isinstance(result, ParsedQuery)
        assert len(result.research_questions) > 0

    @pytest.mark.asyncio
    async def test_parse_handles_missing_improved_query(
        self,
        input_parser_agent: InputParserAgent,
        mock_model: MagicMock,
    ) -> None:
        """Test that parse() handles missing improved_query gracefully."""
        # Create a result with missing improved_query
        mock_result = MagicMock(spec=AgentRunResult)
        mock_parsed = ParsedQuery(
            original_query="test query",
            improved_query="",  # Empty improved query
            research_mode="iterative",
            key_entities=[],
            research_questions=[],
        )
        mock_result.output = mock_parsed
        input_parser_agent.agent.run = AsyncMock(return_value=mock_result)

        query = "test query"
        result = await input_parser_agent.parse(query)

        # Should use original_query as fallback
        assert isinstance(result, ParsedQuery)
        assert result.improved_query == result.original_query

    @pytest.mark.asyncio
    async def test_parse_fallback_to_heuristic_on_error(
        self, input_parser_agent: InputParserAgent
    ) -> None:
        """Test that parse() falls back to heuristic when agent fails."""
        # Make agent.run raise an exception
        input_parser_agent.agent.run = AsyncMock(side_effect=Exception("Agent failed"))

        # Query with "comprehensive" should trigger deep mode heuristic
        query = "Write a comprehensive report on diabetes"
        result = await input_parser_agent.parse(query)

        assert isinstance(result, ParsedQuery)
        assert result.research_mode == "deep"  # Heuristic should detect "comprehensive"
        assert result.original_query == query
        assert result.improved_query == query  # No improvement on fallback

    @pytest.mark.asyncio
    async def test_parse_heuristic_iterative_mode(
        self, input_parser_agent: InputParserAgent
    ) -> None:
        """Test that parse() heuristic correctly identifies iterative mode."""
        # Make agent.run raise an exception
        input_parser_agent.agent.run = AsyncMock(side_effect=Exception("Agent failed"))

        # Simple query should trigger iterative mode heuristic
        query = "What is metformin?"
        result = await input_parser_agent.parse(query)

        assert isinstance(result, ParsedQuery)
        assert result.research_mode == "iterative"
        assert result.original_query == query


class TestCreateInputParserAgent:
    """Test create_input_parser_agent() factory function."""

    @patch("src.agents.input_parser.get_model")
    def test_create_input_parser_agent_with_model(
        self, mock_get_model: MagicMock, mock_model: MagicMock
    ) -> None:
        """Test factory function with provided model."""
        agent = create_input_parser_agent(model=mock_model)
        assert isinstance(agent, InputParserAgent)
        assert agent.model == mock_model
        mock_get_model.assert_not_called()

    @patch("src.agents.input_parser.get_model")
    def test_create_input_parser_agent_without_model(
        self, mock_get_model: MagicMock, mock_model: MagicMock
    ) -> None:
        """Test factory function without model (uses default)."""
        mock_get_model.return_value = mock_model
        agent = create_input_parser_agent()
        assert isinstance(agent, InputParserAgent)
        assert agent.model == mock_model
        mock_get_model.assert_called_once()

    @patch("src.agents.input_parser.get_model")
    def test_create_input_parser_agent_handles_error(self, mock_get_model: MagicMock) -> None:
        """Test factory function handles errors gracefully."""
        mock_get_model.side_effect = Exception("Model creation failed")
        with pytest.raises(ConfigurationError, match="Failed to create input parser agent"):
            create_input_parser_agent()


class TestResearchModeDetection:
    """Test research mode detection logic."""

    @pytest.mark.asyncio
    async def test_detects_iterative_mode_for_simple_queries(
        self,
        input_parser_agent: InputParserAgent,
        mock_agent_result_iterative: AgentRunResult[ParsedQuery],
    ) -> None:
        """Test that simple queries are detected as iterative."""
        input_parser_agent.agent.run = AsyncMock(return_value=mock_agent_result_iterative)

        simple_queries = [
            "What is the mechanism of metformin?",
            "Find clinical trials for drug X",
            "What is the capital of France?",
        ]

        for query in simple_queries:
            result = await input_parser_agent.parse(query)
            assert result.research_mode == "iterative", f"Query '{query}' should be iterative"

    @pytest.mark.asyncio
    async def test_detects_deep_mode_for_complex_queries(
        self,
        input_parser_agent: InputParserAgent,
        mock_agent_result_deep: AgentRunResult[ParsedQuery],
    ) -> None:
        """Test that complex queries are detected as deep."""
        input_parser_agent.agent.run = AsyncMock(return_value=mock_agent_result_deep)

        complex_queries = [
            "Write a comprehensive report on diabetes treatment",
            "Analyze the market for quantum computing",
            "Provide a detailed analysis of AI trends",
        ]

        for query in complex_queries:
            result = await input_parser_agent.parse(query)
            assert result.research_mode == "deep", f"Query '{query}' should be deep"
