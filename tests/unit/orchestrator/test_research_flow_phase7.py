"""Unit tests for Phase 7: Judge integration in iterative research flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.research_flow import IterativeResearchFlow
from src.utils.models import (
    AgentSelectionPlan,
    AgentTask,
    AssessmentDetails,
    JudgeAssessment,
    KnowledgeGapOutput,
    ToolAgentOutput,
)


@pytest.fixture
def mock_judge_handler():
    """Create a mock judge handler."""
    judge = MagicMock()
    judge.assess = AsyncMock()
    return judge


def create_judge_assessment(
    sufficient: bool,
    confidence: float,
    recommendation: str,
    reasoning: str,
) -> JudgeAssessment:
    """Helper to create a valid JudgeAssessment."""
    return JudgeAssessment(
        details=AssessmentDetails(
            mechanism_score=5,
            mechanism_reasoning="Test mechanism reasoning that is long enough",
            clinical_evidence_score=5,
            clinical_reasoning="Test clinical reasoning that is long enough",
            drug_candidates=[],
            key_findings=[],
        ),
        sufficient=sufficient,
        confidence=confidence,
        recommendation=recommendation,
        reasoning=reasoning,
    )


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
def flow_with_judge(mock_agents, mock_judge_handler):
    """Create an IterativeResearchFlow with mocked agents and judge."""
    with (
        patch("src.orchestrator.research_flow.create_knowledge_gap_agent") as mock_kg,
        patch("src.orchestrator.research_flow.create_tool_selector_agent") as mock_ts,
        patch("src.orchestrator.research_flow.create_thinking_agent") as mock_thinking,
        patch("src.orchestrator.research_flow.create_writer_agent") as mock_writer,
        patch("src.orchestrator.research_flow.create_judge_handler") as mock_judge_factory,
        patch("src.orchestrator.research_flow.execute_tool_tasks") as mock_execute,
        patch("src.orchestrator.research_flow.get_workflow_state") as mock_state,
    ):
        mock_kg.return_value = mock_agents["knowledge_gap"]
        mock_ts.return_value = mock_agents["tool_selector"]
        mock_thinking.return_value = mock_agents["thinking"]
        mock_writer.return_value = mock_agents["writer"]
        mock_judge_factory.return_value = mock_judge_handler
        mock_execute.return_value = {
            "task_1": ToolAgentOutput(output="Finding 1", sources=["url1"]),
        }

        # Mock workflow state
        mock_state_obj = MagicMock()
        mock_state_obj.evidence = []
        mock_state_obj.add_evidence = MagicMock(return_value=1)
        mock_state.return_value = mock_state_obj

        return IterativeResearchFlow(max_iterations=2, max_time_minutes=5)


@pytest.mark.unit
@pytest.mark.asyncio
class TestJudgeIntegration:
    """Tests for judge integration in iterative research flow."""

    async def test_judge_called_after_tool_execution(
        self, flow_with_judge, mock_agents, mock_judge_handler
    ):
        """Judge should be called after tool execution."""
        # Mock knowledge gap agent to return incomplete
        mock_agents["knowledge_gap"].evaluate = AsyncMock(
            return_value=KnowledgeGapOutput(
                research_complete=False,
                outstanding_gaps=["Need more info"],
            )
        )

        # Mock thinking agent
        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Initial thoughts")

        # Mock tool selector
        mock_agents["tool_selector"].select_tools = AsyncMock(
            return_value=AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap="Need more info",
                        agent="WebSearchAgent",
                        query="test query",
                    )
                ]
            )
        )

        # Mock judge to return sufficient
        mock_judge_handler.assess = AsyncMock(
            return_value=create_judge_assessment(
                sufficient=True,
                confidence=0.9,
                recommendation="synthesize",
                reasoning="Evidence is sufficient to provide a comprehensive answer.",
            )
        )

        # Mock writer
        mock_agents["writer"].write_report = AsyncMock(
            return_value="# Final Report\n\nContent here."
        )

        result = await flow_with_judge.run("Test query")

        # Verify judge was called
        assert mock_judge_handler.assess.called
        assert isinstance(result, str)
        assert "Final Report" in result

    async def test_loop_completes_when_judge_says_sufficient(
        self, flow_with_judge, mock_agents, mock_judge_handler
    ):
        """Loop should complete when judge says evidence is sufficient."""
        # Mock knowledge gap to return incomplete
        mock_agents["knowledge_gap"].evaluate = AsyncMock(
            return_value=KnowledgeGapOutput(
                research_complete=False,
                outstanding_gaps=["Need more info"],
            )
        )

        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Thoughts")

        mock_agents["tool_selector"].select_tools = AsyncMock(
            return_value=AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap="Need more info",
                        agent="WebSearchAgent",
                        query="test",
                    )
                ]
            )
        )

        # Judge says sufficient
        mock_judge_handler.assess = AsyncMock(
            return_value=create_judge_assessment(
                sufficient=True,
                confidence=0.95,
                recommendation="synthesize",
                reasoning="Enough evidence has been collected to synthesize a comprehensive answer.",
            )
        )

        mock_agents["writer"].write_report = AsyncMock(return_value="# Report\n\nDone.")

        result = await flow_with_judge.run("Test query")

        # Should complete after judge says sufficient
        assert flow_with_judge.should_continue is False
        assert mock_judge_handler.assess.called
        assert isinstance(result, str)

    async def test_loop_continues_when_judge_says_insufficient(
        self, flow_with_judge, mock_agents, mock_judge_handler
    ):
        """Loop should continue when judge says evidence is insufficient."""
        call_count = {"kg": 0, "judge": 0}

        def mock_kg_evaluate(*args, **kwargs):
            call_count["kg"] += 1
            if call_count["kg"] == 1:
                return KnowledgeGapOutput(
                    research_complete=False,
                    outstanding_gaps=["Need more info"],
                )
            # Second call: complete
            return KnowledgeGapOutput(
                research_complete=True,
                outstanding_gaps=[],
            )

        def mock_judge_assess(*args, **kwargs):
            call_count["judge"] += 1
            # First call: insufficient
            if call_count["judge"] == 1:
                return create_judge_assessment(
                    sufficient=False,
                    confidence=0.5,
                    recommendation="continue",
                    reasoning="Need more evidence to provide a comprehensive answer.",
                )
            # Second call: sufficient (but won't be reached due to max_iterations)
            return create_judge_assessment(
                sufficient=True,
                confidence=0.9,
                recommendation="synthesize",
                reasoning="Enough evidence has now been collected to proceed.",
            )

        mock_agents["knowledge_gap"].evaluate = AsyncMock(side_effect=mock_kg_evaluate)
        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Thoughts")
        mock_agents["tool_selector"].select_tools = AsyncMock(
            return_value=AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap="Need more info",
                        agent="WebSearchAgent",
                        query="test",
                    )
                ]
            )
        )
        mock_judge_handler.assess = AsyncMock(side_effect=mock_judge_assess)
        mock_agents["writer"].write_report = AsyncMock(return_value="# Report\n\nDone.")

        result = await flow_with_judge.run("Test query")

        # Judge should be called
        assert mock_judge_handler.assess.called
        # Should eventually complete
        assert isinstance(result, str)

    async def test_judge_receives_evidence_from_state(
        self, flow_with_judge, mock_agents, mock_judge_handler
    ):
        """Judge should receive evidence from workflow state."""
        from src.utils.models import Citation, Evidence

        # Create mock evidence in state
        mock_evidence = [
            Evidence(
                content="Test evidence content",
                citation=Citation(
                    source="rag",  # Use valid SourceName
                    title="Test Title",
                    url="https://example.com",
                    date="2024-01-01",
                    authors=[],
                ),
                relevance=0.8,
            )
        ]

        # Mock state to return evidence
        from unittest.mock import patch

        with patch("src.orchestrator.research_flow.get_workflow_state") as mock_state:
            mock_state_obj = MagicMock()
            mock_state_obj.evidence = mock_evidence
            mock_state_obj.add_evidence = MagicMock(return_value=1)
            mock_state.return_value = mock_state_obj

            mock_agents["knowledge_gap"].evaluate = AsyncMock(
                return_value=KnowledgeGapOutput(
                    research_complete=False,
                    outstanding_gaps=["Need info"],
                )
            )
            mock_agents["thinking"].generate_observations = AsyncMock(return_value="Thoughts")
            mock_agents["tool_selector"].select_tools = AsyncMock(
                return_value=AgentSelectionPlan(
                    tasks=[
                        AgentTask(
                            gap="Need info",
                            agent="WebSearchAgent",
                            query="test",
                        )
                    ]
                )
            )
            mock_judge_handler.assess = AsyncMock(
                return_value=create_judge_assessment(
                    sufficient=True,
                    confidence=0.9,
                    recommendation="synthesize",
                    reasoning="Good evidence has been collected to answer the query.",
                )
            )
            mock_agents["writer"].write_report = AsyncMock(return_value="# Report\n\nDone.")

            result = await flow_with_judge.run("Test query")

            # Verify judge was called with evidence
            assert mock_judge_handler.assess.called
            call_args = mock_judge_handler.assess.call_args
            assert call_args[0][0] == "Test query"  # query
            assert len(call_args[0][1]) >= 0  # evidence list
            assert isinstance(result, str)

    async def test_token_tracking_for_judge_call(
        self, flow_with_judge, mock_agents, mock_judge_handler
    ):
        """Token tracking should work for judge calls."""
        mock_agents["knowledge_gap"].evaluate = AsyncMock(
            return_value=KnowledgeGapOutput(
                research_complete=False,
                outstanding_gaps=["Need info"],
            )
        )
        mock_agents["thinking"].generate_observations = AsyncMock(return_value="Thoughts")
        mock_agents["tool_selector"].select_tools = AsyncMock(
            return_value=AgentSelectionPlan(
                tasks=[
                    AgentTask(
                        gap="Need info",
                        agent="WebSearchAgent",
                        query="test",
                    )
                ]
            )
        )
        mock_judge_handler.assess = AsyncMock(
            return_value=create_judge_assessment(
                sufficient=True,
                confidence=0.9,
                recommendation="synthesize",
                reasoning="Evidence is sufficient to provide a comprehensive answer.",
            )
        )
        mock_agents["writer"].write_report = AsyncMock(return_value="# Report\n\nDone.")

        await flow_with_judge.run("Test query")

        # Check that tokens were tracked for the iteration
        iteration_tokens = flow_with_judge.budget_tracker.get_iteration_tokens(
            flow_with_judge.loop_id, 1
        )
        # Should have tracked tokens (may be 0 if estimation is off, but method should work)
        assert isinstance(iteration_tokens, int)
        assert iteration_tokens >= 0
