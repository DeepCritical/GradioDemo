"""Graph orchestrator for Phase 4.

Implements graph-based orchestration using Pydantic AI agents as nodes.
Supports both iterative and deep research patterns with parallel execution.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING, Any, Literal

import structlog

from src.agent_factory.agents import (
    create_input_parser_agent,
    create_knowledge_gap_agent,
    create_long_writer_agent,
    create_planner_agent,
    create_thinking_agent,
    create_tool_selector_agent,
    create_writer_agent,
)
from src.agent_factory.graph_builder import (
    AgentNode,
    DecisionNode,
    ParallelNode,
    ResearchGraph,
    StateNode,
    create_deep_graph,
    create_iterative_graph,
)
from src.middleware.budget_tracker import BudgetTracker
from src.middleware.state_machine import WorkflowState, init_workflow_state
from src.orchestrator.research_flow import DeepResearchFlow, IterativeResearchFlow
from src.utils.models import AgentEvent

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


class GraphExecutionContext:
    """Context for managing graph execution state."""

    def __init__(self, state: WorkflowState, budget_tracker: BudgetTracker) -> None:
        """Initialize execution context.

        Args:
            state: Current workflow state
            budget_tracker: Budget tracker instance
        """
        self.current_node: str = ""
        self.visited_nodes: set[str] = set()
        self.node_results: dict[str, Any] = {}
        self.state = state
        self.budget_tracker = budget_tracker
        self.iteration_count = 0

    def set_node_result(self, node_id: str, result: Any) -> None:
        """Store result from node execution.

        Args:
            node_id: The node ID
            result: The execution result
        """
        self.node_results[node_id] = result

    def get_node_result(self, node_id: str) -> Any:
        """Get result from node execution.

        Args:
            node_id: The node ID

        Returns:
            The stored result, or None if not found
        """
        return self.node_results.get(node_id)

    def has_visited(self, node_id: str) -> bool:
        """Check if node was visited.

        Args:
            node_id: The node ID

        Returns:
            True if visited, False otherwise
        """
        return node_id in self.visited_nodes

    def mark_visited(self, node_id: str) -> None:
        """Mark node as visited.

        Args:
            node_id: The node ID
        """
        self.visited_nodes.add(node_id)

    def update_state(
        self, updater: Callable[[WorkflowState, Any], WorkflowState], data: Any
    ) -> None:
        """Update workflow state.

        Args:
            updater: Function to update state
            data: Data to pass to updater
        """
        self.state = updater(self.state, data)


class GraphOrchestrator:
    """
    Graph orchestrator using Pydantic AI Graphs.

    Executes research workflows as graphs with nodes (agents) and edges (transitions).
    Supports parallel execution, conditional routing, and state management.
    """

    def __init__(
        self,
        mode: Literal["iterative", "deep", "auto"] = "auto",
        max_iterations: int = 5,
        max_time_minutes: int = 10,
        use_graph: bool = True,
    ) -> None:
        """
        Initialize graph orchestrator.

        Args:
            mode: Research mode ("iterative", "deep", or "auto" to detect)
            max_iterations: Maximum iterations per loop
            max_time_minutes: Maximum time per loop
            use_graph: Whether to use graph execution (True) or agent chains (False)
        """
        self.mode = mode
        self.max_iterations = max_iterations
        self.max_time_minutes = max_time_minutes
        self.use_graph = use_graph
        self.logger = logger

        # Initialize flows (for backward compatibility)
        self._iterative_flow: IterativeResearchFlow | None = None
        self._deep_flow: DeepResearchFlow | None = None

        # Graph execution components (lazy initialization)
        self._graph: ResearchGraph | None = None
        self._budget_tracker: BudgetTracker | None = None

    async def run(self, query: str) -> AsyncGenerator[AgentEvent, None]:
        """
        Run the research workflow.

        Args:
            query: The user's research query

        Yields:
            AgentEvent objects for real-time UI updates
        """
        self.logger.info(
            "Starting graph orchestrator",
            query=query[:100],
            mode=self.mode,
            use_graph=self.use_graph,
        )

        yield AgentEvent(
            type="started",
            message=f"Starting research ({self.mode} mode): {query}",
            iteration=0,
        )

        try:
            # Determine research mode
            research_mode = self.mode
            if research_mode == "auto":
                research_mode = await self._detect_research_mode(query)

            # Use graph execution if enabled, otherwise fall back to agent chains
            if self.use_graph:
                async for event in self._run_with_graph(query, research_mode):
                    yield event
            else:
                async for event in self._run_with_chains(query, research_mode):
                    yield event

        except Exception as e:
            self.logger.error("Graph orchestrator failed", error=str(e), exc_info=True)
            yield AgentEvent(
                type="error",
                message=f"Research failed: {e!s}",
                iteration=0,
            )

    async def _run_with_graph(
        self, query: str, research_mode: Literal["iterative", "deep"]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Run workflow using graph execution.

        Args:
            query: The research query
            research_mode: The research mode

        Yields:
            AgentEvent objects
        """
        # Initialize state and budget tracker
        from src.services.embeddings import get_embedding_service

        embedding_service = get_embedding_service()
        state = init_workflow_state(embedding_service=embedding_service)
        budget_tracker = BudgetTracker()
        budget_tracker.create_budget(
            loop_id="graph_execution",
            tokens_limit=100000,
            time_limit_seconds=self.max_time_minutes * 60,
            iterations_limit=self.max_iterations,
        )
        budget_tracker.start_timer("graph_execution")

        context = GraphExecutionContext(state, budget_tracker)

        # Build graph
        self._graph = await self._build_graph(research_mode)

        # Execute graph
        async for event in self._execute_graph(query, context):
            yield event

    async def _run_with_chains(
        self, query: str, research_mode: Literal["iterative", "deep"]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Run workflow using agent chains (backward compatibility).

        Args:
            query: The research query
            research_mode: The research mode

        Yields:
            AgentEvent objects
        """
        if research_mode == "iterative":
            yield AgentEvent(
                type="searching",
                message="Running iterative research flow...",
                iteration=1,
            )

            if self._iterative_flow is None:
                self._iterative_flow = IterativeResearchFlow(
                    max_iterations=self.max_iterations,
                    max_time_minutes=self.max_time_minutes,
                )

            try:
                final_report = await self._iterative_flow.run(query)
            except Exception as e:
                self.logger.error("Iterative flow failed", error=str(e), exc_info=True)
                # Yield error event - outer handler will also catch and yield error event
                yield AgentEvent(
                    type="error",
                    message=f"Iterative research failed: {e!s}",
                    iteration=1,
                )
                # Re-raise so outer handler can also yield error event for consistency
                raise

            yield AgentEvent(
                type="complete",
                message=final_report,
                data={"mode": "iterative"},
                iteration=1,
            )

        elif research_mode == "deep":
            yield AgentEvent(
                type="searching",
                message="Running deep research flow...",
                iteration=1,
            )

            if self._deep_flow is None:
                self._deep_flow = DeepResearchFlow(
                    max_iterations=self.max_iterations,
                    max_time_minutes=self.max_time_minutes,
                )

            try:
                final_report = await self._deep_flow.run(query)
            except Exception as e:
                self.logger.error("Deep flow failed", error=str(e), exc_info=True)
                # Yield error event before re-raising so test can capture it
                yield AgentEvent(
                    type="error",
                    message=f"Deep research failed: {e!s}",
                    iteration=1,
                )
                raise

            yield AgentEvent(
                type="complete",
                message=final_report,
                data={"mode": "deep"},
                iteration=1,
            )

    async def _build_graph(self, mode: Literal["iterative", "deep"]) -> ResearchGraph:
        """Build graph for the specified mode.

        Args:
            mode: Research mode

        Returns:
            Constructed ResearchGraph
        """
        if mode == "iterative":
            # Get agents
            knowledge_gap_agent = create_knowledge_gap_agent()
            tool_selector_agent = create_tool_selector_agent()
            thinking_agent = create_thinking_agent()
            writer_agent = create_writer_agent()

            # Create graph
            graph = create_iterative_graph(
                knowledge_gap_agent=knowledge_gap_agent.agent,
                tool_selector_agent=tool_selector_agent.agent,
                thinking_agent=thinking_agent.agent,
                writer_agent=writer_agent.agent,
            )
        else:  # deep
            # Get agents
            planner_agent = create_planner_agent()
            knowledge_gap_agent = create_knowledge_gap_agent()
            tool_selector_agent = create_tool_selector_agent()
            thinking_agent = create_thinking_agent()
            writer_agent = create_writer_agent()
            long_writer_agent = create_long_writer_agent()

            # Create graph
            graph = create_deep_graph(
                planner_agent=planner_agent.agent,
                knowledge_gap_agent=knowledge_gap_agent.agent,
                tool_selector_agent=tool_selector_agent.agent,
                thinking_agent=thinking_agent.agent,
                writer_agent=writer_agent.agent,
                long_writer_agent=long_writer_agent.agent,
            )

        return graph

    def _emit_start_event(
        self, node: Any, current_node_id: str, iteration: int, context: GraphExecutionContext
    ) -> AgentEvent:
        """Emit start event for a node.

        Args:
            node: The node being executed
            current_node_id: Current node ID
            iteration: Current iteration number
            context: Execution context

        Returns:
            AgentEvent for the start of node execution
        """
        if node and node.node_id == "planner":
            return AgentEvent(
                type="searching",
                message="Creating report plan...",
                iteration=iteration,
            )
        elif node and node.node_id == "parallel_loops":
            # Get report plan to show section count
            report_plan = context.get_node_result("planner")
            if report_plan and hasattr(report_plan, "report_outline"):
                section_count = len(report_plan.report_outline)
                return AgentEvent(
                    type="looping",
                    message=f"Running parallel research loops for {section_count} sections...",
                    iteration=iteration,
                    data={"sections": section_count},
                )
            return AgentEvent(
                type="looping",
                message="Running parallel research loops...",
                iteration=iteration,
            )
        elif node and node.node_id == "synthesizer":
            return AgentEvent(
                type="synthesizing",
                message="Synthesizing final report from section drafts...",
                iteration=iteration,
            )
        return AgentEvent(
            type="looping",
            message=f"Executing node: {current_node_id}",
            iteration=iteration,
        )

    def _emit_completion_event(
        self, node: Any, current_node_id: str, result: Any, iteration: int
    ) -> AgentEvent:
        """Emit completion event for a node.

        Args:
            node: The node that was executed
            current_node_id: Current node ID
            result: Node execution result
            iteration: Current iteration number

        Returns:
            AgentEvent for the completion of node execution
        """
        if not node:
            return AgentEvent(
                type="looping",
                message=f"Completed node: {current_node_id}",
                iteration=iteration,
            )

        if node.node_id == "planner":
            if isinstance(result, dict) and "report_outline" in result:
                section_count = len(result["report_outline"])
                return AgentEvent(
                    type="search_complete",
                    message=f"Report plan created with {section_count} sections",
                    iteration=iteration,
                    data={"sections": section_count},
                )
            return AgentEvent(
                type="search_complete",
                message="Report plan created",
                iteration=iteration,
            )
        elif node.node_id == "parallel_loops":
            if isinstance(result, list):
                return AgentEvent(
                    type="search_complete",
                    message=f"Completed parallel research for {len(result)} sections",
                    iteration=iteration,
                    data={"sections_completed": len(result)},
                )
            return AgentEvent(
                type="search_complete",
                message="Parallel research loops completed",
                iteration=iteration,
            )
        elif node.node_id == "synthesizer":
            return AgentEvent(
                type="synthesizing",
                message="Final report synthesis completed",
                iteration=iteration,
            )
        return AgentEvent(
            type="searching" if node.node_type == "agent" else "looping",
            message=f"Completed {node.node_type} node: {current_node_id}",
            iteration=iteration,
        )

    async def _execute_graph(
        self, query: str, context: GraphExecutionContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute the graph from entry node.

        Args:
            query: The research query
            context: Execution context

        Yields:
            AgentEvent objects
        """
        if not self._graph:
            raise ValueError("Graph not built")

        current_node_id = self._graph.entry_node
        iteration = 0

        while current_node_id and current_node_id not in self._graph.exit_nodes:
            # Check budget
            if not context.budget_tracker.can_continue("graph_execution"):
                self.logger.warning("Budget exceeded, exiting graph execution")
                break

            # Execute current node
            iteration += 1
            context.current_node = current_node_id
            node = self._graph.get_node(current_node_id)

            # Emit start event
            yield self._emit_start_event(node, current_node_id, iteration, context)

            try:
                result = await self._execute_node(current_node_id, query, context)
                context.set_node_result(current_node_id, result)
                context.mark_visited(current_node_id)

                # Yield completion event
                yield self._emit_completion_event(node, current_node_id, result, iteration)

            except Exception as e:
                self.logger.error("Node execution failed", node_id=current_node_id, error=str(e))
                yield AgentEvent(
                    type="error",
                    message=f"Node {current_node_id} failed: {e!s}",
                    iteration=iteration,
                )
                break

            # Get next node(s)
            next_nodes = self._get_next_node(current_node_id, context)

            if not next_nodes:
                # No more nodes, check if we're at exit
                if current_node_id in self._graph.exit_nodes:
                    break
                # Otherwise, we've reached a dead end
                self.logger.warning("Reached dead end in graph", node_id=current_node_id)
                break

            current_node_id = next_nodes[0]  # For now, take first next node (handle parallel later)

        # Final event
        final_result = context.get_node_result(current_node_id) if current_node_id else None
        yield AgentEvent(
            type="complete",
            message=final_result if isinstance(final_result, str) else "Research completed",
            data={"mode": self.mode, "iterations": iteration},
            iteration=iteration,
        )

    async def _execute_node(self, node_id: str, query: str, context: GraphExecutionContext) -> Any:
        """Execute a single node.

        Args:
            node_id: The node ID
            query: The research query
            context: Execution context

        Returns:
            Node execution result
        """
        if not self._graph:
            raise ValueError("Graph not built")

        node = self._graph.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        if isinstance(node, AgentNode):
            return await self._execute_agent_node(node, query, context)
        elif isinstance(node, StateNode):
            return await self._execute_state_node(node, query, context)
        elif isinstance(node, DecisionNode):
            return await self._execute_decision_node(node, query, context)
        elif isinstance(node, ParallelNode):
            return await self._execute_parallel_node(node, query, context)
        else:
            raise ValueError(f"Unknown node type: {type(node)}")

    async def _execute_agent_node(
        self, node: AgentNode, query: str, context: GraphExecutionContext
    ) -> Any:
        """Execute an agent node.

        Special handling for deep research nodes:
        - "planner": Takes query string, returns ReportPlan
        - "synthesizer": Takes query + ReportPlan + section drafts, returns final report

        Args:
            node: The agent node
            query: The research query
            context: Execution context

        Returns:
            Agent execution result
        """
        # Special handling for synthesizer node
        if node.node_id == "synthesizer":
            # Call LongWriterAgent.write_report() directly instead of using agent.run()
            from src.agent_factory.agents import create_long_writer_agent
            from src.utils.models import ReportDraft, ReportDraftSection, ReportPlan

            report_plan = context.get_node_result("planner")
            section_drafts = context.get_node_result("parallel_loops") or []

            if not isinstance(report_plan, ReportPlan):
                raise ValueError("ReportPlan not found for synthesizer")

            if not section_drafts:
                raise ValueError("Section drafts not found for synthesizer")

            # Create ReportDraft from section drafts
            report_draft = ReportDraft(
                sections=[
                    ReportDraftSection(
                        section_title=section.title,
                        section_content=draft,
                    )
                    for section, draft in zip(
                        report_plan.report_outline, section_drafts, strict=False
                    )
                ]
            )

            # Get LongWriterAgent instance and call write_report directly
            long_writer_agent = create_long_writer_agent()
            final_report = await long_writer_agent.write_report(
                original_query=query,
                report_title=report_plan.report_title,
                report_draft=report_draft,
            )

            # Estimate tokens (rough estimate)
            estimated_tokens = len(final_report) // 4  # Rough token estimate
            context.budget_tracker.add_tokens("graph_execution", estimated_tokens)

            return final_report

        # Standard agent execution
        # Prepare input based on node type
        if node.node_id == "planner":
            # Planner takes the original query
            input_data = query
        else:
            # Standard: use previous node result or query
            prev_result = context.get_node_result(context.current_node)
            input_data = prev_result if prev_result is not None else query

        # Apply input transformer if provided
        if node.input_transformer:
            input_data = node.input_transformer(input_data)

        # Execute agent
        result = await node.agent.run(input_data)

        # Transform output if needed
        output = result.output
        if node.output_transformer:
            output = node.output_transformer(output)

        # Estimate and track tokens
        if hasattr(result, "usage") and result.usage:
            tokens = result.usage.total_tokens if hasattr(result.usage, "total_tokens") else 0
            context.budget_tracker.add_tokens("graph_execution", tokens)

        return output

    async def _execute_state_node(
        self, node: StateNode, query: str, context: GraphExecutionContext
    ) -> Any:
        """Execute a state node.

        Special handling for deep research state nodes:
        - "store_plan": Stores ReportPlan in context for parallel loops
        - "collect_drafts": Stores section drafts in context for synthesizer

        Args:
            node: The state node
            query: The research query
            context: Execution context

        Returns:
            State update result
        """
        # Get previous result for state update
        # For "store_plan", get from planner node
        # For "collect_drafts", get from parallel_loops node
        if node.node_id == "store_plan":
            prev_result = context.get_node_result("planner")
        elif node.node_id == "collect_drafts":
            prev_result = context.get_node_result("parallel_loops")
        else:
            prev_result = context.get_node_result(context.current_node)

        # Update state
        updated_state = node.state_updater(context.state, prev_result)
        context.state = updated_state

        # Store result in context for next nodes to access
        context.set_node_result(node.node_id, prev_result)

        # Read state if needed
        if node.state_reader:
            return node.state_reader(context.state)

        return prev_result  # Return the stored result for next nodes

    async def _execute_decision_node(
        self, node: DecisionNode, query: str, context: GraphExecutionContext
    ) -> str:
        """Execute a decision node.

        Args:
            node: The decision node
            query: The research query
            context: Execution context

        Returns:
            Next node ID
        """
        # Get previous result for decision
        prev_result = context.get_node_result(context.current_node)

        # Make decision
        next_node_id = node.decision_function(prev_result)

        # Validate decision
        if next_node_id not in node.options:
            self.logger.warning(
                "Decision function returned invalid node",
                node_id=node.node_id,
                returned=next_node_id,
                options=node.options,
            )
            # Default to first option
            next_node_id = node.options[0]

        return next_node_id

    async def _execute_parallel_node(
        self, node: ParallelNode, query: str, context: GraphExecutionContext
    ) -> list[Any]:
        """Execute a parallel node.

        Special handling for deep research "parallel_loops" node:
        - Extracts report plan from previous node result
        - Creates IterativeResearchFlow instances for each section
        - Executes them in parallel
        - Returns section drafts

        Args:
            node: The parallel node
            query: The research query
            context: Execution context

        Returns:
            List of results from parallel nodes
        """
        # Special handling for deep research parallel_loops node
        if node.node_id == "parallel_loops":
            return await self._execute_deep_research_parallel_loops(node, query, context)

        # Standard parallel node execution
        # Execute all parallel nodes concurrently
        tasks = [
            self._execute_node(parallel_node_id, query, context)
            for parallel_node_id in node.parallel_nodes
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Parallel node execution failed",
                    node_id=node.parallel_nodes[i] if i < len(node.parallel_nodes) else "unknown",
                    error=str(result),
                )
                results[i] = None

        # Aggregate if needed
        if node.aggregator:
            aggregated = node.aggregator(results)
            # Type cast: aggregator returns Any, but we expect list[Any]
            return list(aggregated) if isinstance(aggregated, list) else [aggregated]

        return results

    async def _execute_deep_research_parallel_loops(
        self, node: ParallelNode, query: str, context: GraphExecutionContext
    ) -> list[str]:
        """Execute parallel iterative research loops for deep research.

        Args:
            node: The parallel node (should be "parallel_loops")
            query: The research query
            context: Execution context

        Returns:
            List of section draft strings
        """
        from src.agent_factory.judges import create_judge_handler
        from src.orchestrator.research_flow import IterativeResearchFlow
        from src.utils.models import ReportPlan

        # Get report plan from previous node (store_plan)
        # The plan should be stored in context.node_results from the planner node
        planner_result = context.get_node_result("planner")
        if not isinstance(planner_result, ReportPlan):
            self.logger.error(
                "Planner result is not a ReportPlan",
                type=type(planner_result),
            )
            raise ValueError("Planner must return ReportPlan for deep research")

        report_plan: ReportPlan = planner_result
        self.logger.info(
            "Executing parallel loops for deep research",
            sections=len(report_plan.report_outline),
        )

        # Create judge handler for iterative flows
        judge_handler = create_judge_handler()

        # Create and execute iterative research flows for each section
        async def run_section_research(section_index: int) -> str:
            """Run iterative research for a single section."""
            section = report_plan.report_outline[section_index]

            try:
                # Create iterative research flow
                flow = IterativeResearchFlow(
                    max_iterations=self.max_iterations,
                    max_time_minutes=self.max_time_minutes,
                    verbose=False,  # Less verbose in parallel execution
                    use_graph=False,  # Use agent chains for section research
                    judge_handler=judge_handler,
                )

                # Run research for this section
                section_draft = await flow.run(
                    query=section.key_question,
                    background_context=report_plan.background_context,
                )

                self.logger.info(
                    "Section research completed",
                    section_index=section_index,
                    section_title=section.title,
                    draft_length=len(section_draft),
                )

                return section_draft

            except Exception as e:
                self.logger.error(
                    "Section research failed",
                    section_index=section_index,
                    section_title=section.title,
                    error=str(e),
                )
                # Return empty string for failed sections
                return f"# {section.title}\n\n[Research failed: {e!s}]"

        # Execute all sections in parallel
        section_drafts = await asyncio.gather(
            *(run_section_research(i) for i in range(len(report_plan.report_outline))),
            return_exceptions=True,
        )

        # Handle exceptions and filter None results
        filtered_drafts: list[str] = []
        for i, draft in enumerate(section_drafts):
            if isinstance(draft, Exception):
                self.logger.error(
                    "Section research exception",
                    section_index=i,
                    error=str(draft),
                )
                filtered_drafts.append(
                    f"# {report_plan.report_outline[i].title}\n\n[Research failed: {draft!s}]"
                )
            elif draft is not None:
                # Type narrowing: after Exception check, draft is str | None
                assert isinstance(draft, str), "Expected str after Exception check"
                filtered_drafts.append(draft)

        self.logger.info(
            "Parallel loops completed",
            sections=len(filtered_drafts),
            total_sections=len(report_plan.report_outline),
        )

        return filtered_drafts

    def _get_next_node(self, node_id: str, context: GraphExecutionContext) -> list[str]:
        """Get next node(s) from current node.

        Args:
            node_id: Current node ID
            context: Execution context

        Returns:
            List of next node IDs
        """
        if not self._graph:
            return []

        # Get node result for condition evaluation
        node_result = context.get_node_result(node_id)

        # Get next nodes
        next_nodes = self._graph.get_next_nodes(node_id, context=node_result)

        # If this was a decision node, use its result
        node = self._graph.get_node(node_id)
        if isinstance(node, DecisionNode):
            decision_result = node_result
            if isinstance(decision_result, str):
                return [decision_result]

        # Return next node IDs
        return [next_node_id for next_node_id, _ in next_nodes]

    async def _detect_research_mode(self, query: str) -> Literal["iterative", "deep"]:
        """
        Detect research mode from query using input parser agent.

        Uses input parser agent to analyze query and determine research mode.
        Falls back to heuristic if parser fails.

        Args:
            query: The research query

        Returns:
            Detected research mode
        """
        try:
            # Use input parser agent for intelligent mode detection
            input_parser = create_input_parser_agent()
            parsed_query = await input_parser.parse(query)
            self.logger.info(
                "Research mode detected by input parser",
                mode=parsed_query.research_mode,
                query=query[:100],
            )
            return parsed_query.research_mode
        except Exception as e:
            # Fallback to heuristic if parser fails
            self.logger.warning(
                "Input parser failed, using heuristic",
                error=str(e),
                query=query[:100],
            )
            query_lower = query.lower()
            if any(
                keyword in query_lower
                for keyword in [
                    "section",
                    "sections",
                    "report",
                    "outline",
                    "structure",
                    "comprehensive",
                    "analyze",
                    "analysis",
                ]
            ):
                return "deep"
            return "iterative"


def create_graph_orchestrator(
    mode: Literal["iterative", "deep", "auto"] = "auto",
    max_iterations: int = 5,
    max_time_minutes: int = 10,
    use_graph: bool = True,
) -> GraphOrchestrator:
    """
    Factory function to create a graph orchestrator.

    Args:
        mode: Research mode
        max_iterations: Maximum iterations per loop
        max_time_minutes: Maximum time per loop
        use_graph: Whether to use graph execution (True) or agent chains (False)

    Returns:
        Configured GraphOrchestrator instance
    """
    return GraphOrchestrator(
        mode=mode,
        max_iterations=max_iterations,
        max_time_minutes=max_time_minutes,
        use_graph=use_graph,
    )
