"""Research flow implementations for iterative and deep research patterns.

Converts the folder/iterative_research.py and folder/deep_research.py
implementations to use Pydantic AI agents.
"""

import asyncio
import time
from typing import Any

import structlog

from src.agent_factory.agents import (
    create_graph_orchestrator,
    create_knowledge_gap_agent,
    create_long_writer_agent,
    create_planner_agent,
    create_proofreader_agent,
    create_thinking_agent,
    create_tool_selector_agent,
    create_writer_agent,
)
from src.agent_factory.judges import create_judge_handler
from src.middleware.budget_tracker import BudgetTracker
from src.middleware.state_machine import get_workflow_state, init_workflow_state
from src.middleware.workflow_manager import WorkflowManager
from src.services.llamaindex_rag import LlamaIndexRAGService, get_rag_service
from src.tools.tool_executor import execute_tool_tasks
from src.utils.exceptions import ConfigurationError
from src.utils.models import (
    AgentSelectionPlan,
    AgentTask,
    Citation,
    Conversation,
    Evidence,
    JudgeAssessment,
    KnowledgeGapOutput,
    ReportDraft,
    ReportDraftSection,
    ReportPlan,
    SourceName,
    ToolAgentOutput,
)

logger = structlog.get_logger()


class IterativeResearchFlow:
    """
    Iterative research flow that runs a single research loop.

    Pattern: Generate observations → Evaluate gaps → Select tools → Execute → Repeat
    until research is complete or constraints are met.
    """

    def __init__(
        self,
        max_iterations: int = 5,
        max_time_minutes: int = 10,
        verbose: bool = True,
        use_graph: bool = False,
        judge_handler: Any | None = None,
    ) -> None:
        """
        Initialize iterative research flow.

        Args:
            max_iterations: Maximum number of iterations
            max_time_minutes: Maximum time in minutes
            verbose: Whether to log progress
            use_graph: Whether to use graph-based execution (True) or agent chains (False)
        """
        self.max_iterations = max_iterations
        self.max_time_minutes = max_time_minutes
        self.verbose = verbose
        self.use_graph = use_graph
        self.logger = logger

        # Initialize agents (only needed for agent chain execution)
        if not use_graph:
            self.knowledge_gap_agent = create_knowledge_gap_agent()
            self.tool_selector_agent = create_tool_selector_agent()
            self.thinking_agent = create_thinking_agent()
            self.writer_agent = create_writer_agent()
            # Initialize judge handler (use provided or create new)
            self.judge_handler = judge_handler or create_judge_handler()

        # Initialize state (only needed for agent chain execution)
        if not use_graph:
            self.conversation = Conversation()
            self.iteration = 0
            self.start_time: float | None = None
            self.should_continue = True

            # Initialize budget tracker
            self.budget_tracker = BudgetTracker()
            self.loop_id = "iterative_flow"
            self.budget_tracker.create_budget(
                loop_id=self.loop_id,
                tokens_limit=100000,
                time_limit_seconds=max_time_minutes * 60,
                iterations_limit=max_iterations,
            )
            self.budget_tracker.start_timer(self.loop_id)

            # Initialize RAG service (lazy, may be None if unavailable)
            self._rag_service: LlamaIndexRAGService | None = None

        # Graph orchestrator (lazy initialization)
        self._graph_orchestrator: Any = None

    async def run(
        self,
        query: str,
        background_context: str = "",
        output_length: str = "",
        output_instructions: str = "",
    ) -> str:
        """
        Run the iterative research flow.

        Args:
            query: The research query
            background_context: Optional background context
            output_length: Optional description of desired output length
            output_instructions: Optional additional instructions

        Returns:
            Final report string
        """
        if self.use_graph:
            return await self._run_with_graph(
                query, background_context, output_length, output_instructions
            )
        else:
            return await self._run_with_chains(
                query, background_context, output_length, output_instructions
            )

    async def _run_with_chains(
        self,
        query: str,
        background_context: str = "",
        output_length: str = "",
        output_instructions: str = "",
    ) -> str:
        """
        Run the iterative research flow using agent chains.

        Args:
            query: The research query
            background_context: Optional background context
            output_length: Optional description of desired output length
            output_instructions: Optional additional instructions

        Returns:
            Final report string
        """
        self.start_time = time.time()
        self.logger.info("Starting iterative research (agent chains)", query=query[:100])

        # Initialize conversation with first iteration
        self.conversation.add_iteration()

        # Main research loop
        while self.should_continue and self._check_constraints():
            self.iteration += 1
            self.logger.info("Starting iteration", iteration=self.iteration)

            # Add new iteration to conversation
            self.conversation.add_iteration()

            # 1. Generate observations
            await self._generate_observations(query, background_context)

            # 2. Evaluate gaps
            evaluation = await self._evaluate_gaps(query, background_context)

            # 3. Assess with judge (after tools execute, we'll assess again)
            # For now, check knowledge gap evaluation
            # After tool execution, we'll do a full judge assessment

            # Check if research is complete (knowledge gap agent says complete)
            if evaluation.research_complete:
                self.should_continue = False
                self.logger.info("Research marked as complete by knowledge gap agent")
                break

            # 4. Select tools for next gap
            next_gap = evaluation.outstanding_gaps[0] if evaluation.outstanding_gaps else query
            selection_plan = await self._select_agents(next_gap, query, background_context)

            # 5. Execute tools
            await self._execute_tools(selection_plan.tasks)

            # 6. Assess evidence sufficiency with judge
            judge_assessment = await self._assess_with_judge(query)

            # Check if judge says evidence is sufficient
            if judge_assessment.sufficient:
                self.should_continue = False
                self.logger.info(
                    "Research marked as complete by judge",
                    confidence=judge_assessment.confidence,
                    reasoning=judge_assessment.reasoning[:100],
                )
                break

            # Update budget tracker
            self.budget_tracker.increment_iteration(self.loop_id)
            self.budget_tracker.update_timer(self.loop_id)

        # Create final report
        report = await self._create_final_report(query, output_length, output_instructions)

        elapsed = time.time() - (self.start_time or time.time())
        self.logger.info(
            "Iterative research completed",
            iterations=self.iteration,
            elapsed_minutes=elapsed / 60,
        )

        return report

    async def _run_with_graph(
        self,
        query: str,
        background_context: str = "",
        output_length: str = "",
        output_instructions: str = "",
    ) -> str:
        """
        Run the iterative research flow using graph execution.

        Args:
            query: The research query
            background_context: Optional background context (currently ignored in graph execution)
            output_length: Optional description of desired output length (currently ignored in graph execution)
            output_instructions: Optional additional instructions (currently ignored in graph execution)

        Returns:
            Final report string
        """
        self.logger.info("Starting iterative research (graph execution)", query=query[:100])

        # Create graph orchestrator (lazy initialization)
        if self._graph_orchestrator is None:
            self._graph_orchestrator = create_graph_orchestrator(
                mode="iterative",
                max_iterations=self.max_iterations,
                max_time_minutes=self.max_time_minutes,
                use_graph=True,
            )

        # Run orchestrator and collect events
        final_report = ""
        async for event in self._graph_orchestrator.run(query):
            if event.type == "complete":
                final_report = event.message
                break
            elif event.type == "error":
                self.logger.error("Graph execution error", error=event.message)
                raise RuntimeError(f"Graph execution failed: {event.message}")

        if not final_report:
            self.logger.warning("No complete event received from graph orchestrator")
            final_report = "Research completed but no report was generated."

        self.logger.info("Iterative research completed (graph execution)")

        return final_report

    def _check_constraints(self) -> bool:
        """Check if we've exceeded constraints."""
        if self.iteration >= self.max_iterations:
            self.logger.info("Max iterations reached", max=self.max_iterations)
            return False

        if self.start_time:
            elapsed_minutes = (time.time() - self.start_time) / 60
            if elapsed_minutes >= self.max_time_minutes:
                self.logger.info("Max time reached", max=self.max_time_minutes)
                return False

        # Check budget tracker
        self.budget_tracker.update_timer(self.loop_id)
        exceeded, reason = self.budget_tracker.check_budget(self.loop_id)
        if exceeded:
            self.logger.info("Budget exceeded", reason=reason)
            return False

        return True

    async def _generate_observations(self, query: str, background_context: str = "") -> str:
        """Generate observations from current research state."""
        # Build input prompt for token estimation
        conversation_history = self.conversation.compile_conversation_history()
        # Build background context section separately to avoid backslash in f-string
        background_section = (
            f"BACKGROUND CONTEXT:\n{background_context}\n\n" if background_context else ""
        )
        input_prompt = f"""
You are starting iteration {self.iteration} of your research process.

ORIGINAL QUERY:
{query}

{background_section}HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
{conversation_history or "No previous actions, findings or thoughts available."}
"""

        observations = await self.thinking_agent.generate_observations(
            query=query,
            background_context=background_context,
            conversation_history=conversation_history,
            iteration=self.iteration,
        )

        # Track tokens for this iteration
        estimated_tokens = self.budget_tracker.estimate_llm_call_tokens(input_prompt, observations)
        self.budget_tracker.add_iteration_tokens(self.loop_id, self.iteration, estimated_tokens)
        self.logger.debug(
            "Tokens tracked for thinking agent",
            iteration=self.iteration,
            tokens=estimated_tokens,
        )

        self.conversation.set_latest_thought(observations)
        return observations

    async def _evaluate_gaps(self, query: str, background_context: str = "") -> KnowledgeGapOutput:
        """Evaluate knowledge gaps in current research."""
        if self.start_time:
            elapsed_minutes = (time.time() - self.start_time) / 60
        else:
            elapsed_minutes = 0.0

        # Build input prompt for token estimation
        conversation_history = self.conversation.compile_conversation_history()
        background = f"BACKGROUND CONTEXT:\n{background_context}" if background_context else ""
        input_prompt = f"""
Current Iteration Number: {self.iteration}
Time Elapsed: {elapsed_minutes:.2f} minutes of maximum {self.max_time_minutes} minutes

ORIGINAL QUERY:
{query}

{background}

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
{conversation_history or "No previous actions, findings or thoughts available."}
"""

        evaluation = await self.knowledge_gap_agent.evaluate(
            query=query,
            background_context=background_context,
            conversation_history=conversation_history,
            iteration=self.iteration,
            time_elapsed_minutes=elapsed_minutes,
            max_time_minutes=self.max_time_minutes,
        )

        # Track tokens for this iteration
        evaluation_text = f"research_complete={evaluation.research_complete}, gaps={len(evaluation.outstanding_gaps)}"
        estimated_tokens = self.budget_tracker.estimate_llm_call_tokens(
            input_prompt, evaluation_text
        )
        self.budget_tracker.add_iteration_tokens(self.loop_id, self.iteration, estimated_tokens)
        self.logger.debug(
            "Tokens tracked for knowledge gap agent",
            iteration=self.iteration,
            tokens=estimated_tokens,
        )

        if not evaluation.research_complete and evaluation.outstanding_gaps:
            self.conversation.set_latest_gap(evaluation.outstanding_gaps[0])

        return evaluation

    async def _assess_with_judge(self, query: str) -> JudgeAssessment:
        """Assess evidence sufficiency using JudgeHandler.

        Args:
            query: The research query

        Returns:
            JudgeAssessment with sufficiency evaluation
        """
        state = get_workflow_state()
        evidence = state.evidence  # Get all collected evidence

        self.logger.info(
            "Assessing evidence with judge",
            query=query[:100],
            evidence_count=len(evidence),
        )

        assessment = await self.judge_handler.assess(query, evidence)

        # Track tokens for judge call
        # Estimate tokens from query + evidence + assessment
        evidence_text = "\n".join([e.content[:500] for e in evidence[:10]])  # Sample
        estimated_tokens = self.budget_tracker.estimate_llm_call_tokens(
            query + evidence_text, str(assessment.reasoning)
        )
        self.budget_tracker.add_iteration_tokens(self.loop_id, self.iteration, estimated_tokens)

        self.logger.info(
            "Judge assessment complete",
            sufficient=assessment.sufficient,
            confidence=assessment.confidence,
            recommendation=assessment.recommendation,
        )

        return assessment

    async def _select_agents(
        self, gap: str, query: str, background_context: str = ""
    ) -> AgentSelectionPlan:
        """Select tools to address knowledge gap."""
        # Build input prompt for token estimation
        conversation_history = self.conversation.compile_conversation_history()
        background = f"BACKGROUND CONTEXT:\n{background_context}" if background_context else ""
        input_prompt = f"""
ORIGINAL QUERY:
{query}

KNOWLEDGE GAP TO ADDRESS:
{gap}

{background}

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
{conversation_history or "No previous actions, findings or thoughts available."}
"""

        selection_plan = await self.tool_selector_agent.select_tools(
            gap=gap,
            query=query,
            background_context=background_context,
            conversation_history=conversation_history,
        )

        # Track tokens for this iteration
        selection_text = f"tasks={len(selection_plan.tasks)}, agents={[task.agent for task in selection_plan.tasks]}"
        estimated_tokens = self.budget_tracker.estimate_llm_call_tokens(
            input_prompt, selection_text
        )
        self.budget_tracker.add_iteration_tokens(self.loop_id, self.iteration, estimated_tokens)
        self.logger.debug(
            "Tokens tracked for tool selector agent",
            iteration=self.iteration,
            tokens=estimated_tokens,
        )

        # Store tool calls in conversation
        tool_calls = [
            f"[Agent] {task.agent} [Query] {task.query} [Entity] {task.entity_website or 'null'}"
            for task in selection_plan.tasks
        ]
        self.conversation.set_latest_tool_calls(tool_calls)

        return selection_plan

    def _get_rag_service(self) -> LlamaIndexRAGService | None:
        """
        Get or create RAG service instance.

        Returns:
            RAG service instance, or None if unavailable
        """
        if self._rag_service is None:
            try:
                self._rag_service = get_rag_service()
                self.logger.info("RAG service initialized for research flow")
            except (ConfigurationError, ImportError) as e:
                self.logger.warning(
                    "RAG service unavailable", error=str(e), hint="OPENAI_API_KEY required"
                )
                return None
        return self._rag_service

    async def _execute_tools(self, tasks: list[AgentTask]) -> dict[str, ToolAgentOutput]:
        """Execute selected tools concurrently."""
        try:
            results = await execute_tool_tasks(tasks)
        except Exception as e:
            # Handle tool execution errors gracefully
            self.logger.error(
                "Tool execution failed",
                error=str(e),
                task_count=len(tasks),
                exc_info=True,
            )
            # Return empty results to allow research flow to continue
            # The flow can still generate a report based on previous iterations
            results = {}

        # Store findings in conversation (only if we have results)
        evidence_list: list[Evidence] = []
        if results:
            findings = [result.output for result in results.values()]
            self.conversation.set_latest_findings(findings)

            # Convert tool outputs to Evidence objects and store in workflow state
            evidence_list = self._convert_tool_outputs_to_evidence(results)

        if evidence_list:
            state = get_workflow_state()
            added_count = state.add_evidence(evidence_list)
            self.logger.info(
                "Evidence added to workflow state",
                count=added_count,
                total_evidence=len(state.evidence),
            )

            # Ingest evidence into RAG if available (Phase 6 requirement)
            rag_service = self._get_rag_service()
            if rag_service is not None:
                try:
                    # ingest_evidence is synchronous, run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, rag_service.ingest_evidence, evidence_list)
                    self.logger.info(
                        "Evidence ingested into RAG",
                        count=len(evidence_list),
                    )
                except Exception as e:
                    # Don't fail the research loop if RAG ingestion fails
                    self.logger.warning(
                        "Failed to ingest evidence into RAG",
                        error=str(e),
                        count=len(evidence_list),
                    )

        return results

    def _convert_tool_outputs_to_evidence(
        self, tool_results: dict[str, ToolAgentOutput]
    ) -> list[Evidence]:
        """Convert ToolAgentOutput to Evidence objects.

        Args:
            tool_results: Dictionary of tool execution results

        Returns:
            List of Evidence objects
        """
        evidence_list = []
        for key, result in tool_results.items():
            # Extract URLs from sources
            if result.sources:
                # Create one Evidence object per source URL
                for url in result.sources:
                    # Determine source type from URL or tool name
                    # Default to "web" for unknown web sources
                    source_type: SourceName = "web"
                    if "pubmed" in url.lower() or "ncbi" in url.lower():
                        source_type = "pubmed"
                    elif "clinicaltrials" in url.lower():
                        source_type = "clinicaltrials"
                    elif "europepmc" in url.lower():
                        source_type = "europepmc"
                    elif "biorxiv" in url.lower():
                        source_type = "biorxiv"
                    elif "arxiv" in url.lower() or "preprint" in url.lower():
                        source_type = "preprint"
                    # Note: "web" is now a valid SourceName for general web sources

                    citation = Citation(
                        title=f"Tool Result: {key}",
                        url=url,
                        source=source_type,
                        date="n.d.",
                        authors=[],
                    )
                    # Truncate content to reasonable length for judge (1500 chars)
                    content = result.output[:1500]
                    if len(result.output) > 1500:
                        content += "... [truncated]"

                    evidence = Evidence(
                        content=content,
                        citation=citation,
                        relevance=0.5,  # Default relevance
                    )
                    evidence_list.append(evidence)
            else:
                # No URLs, create a single Evidence object with tool output
                # Use a placeholder URL based on the tool name
                # Determine source type from tool name
                tool_source_type: SourceName = "web"  # Default for unknown sources
                if "RAG" in key:
                    tool_source_type = "rag"
                elif "WebSearch" in key or "SiteCrawler" in key:
                    tool_source_type = "web"
                # "web" is now a valid SourceName for general web sources

                citation = Citation(
                    title=f"Tool Result: {key}",
                    url=f"tool://{key}",
                    source=tool_source_type,
                    date="n.d.",
                    authors=[],
                )
                content = result.output[:1500]
                if len(result.output) > 1500:
                    content += "... [truncated]"

                evidence = Evidence(
                    content=content,
                    citation=citation,
                    relevance=0.5,
                )
                evidence_list.append(evidence)

        return evidence_list

    async def _create_final_report(
        self, query: str, length: str = "", instructions: str = ""
    ) -> str:
        """Create final report from all findings."""
        all_findings = "\n\n".join(self.conversation.get_all_findings())
        if not all_findings:
            all_findings = "No findings available yet."

        # Build input prompt for token estimation
        length_str = f"* The full response should be approximately {length}.\n" if length else ""
        instructions_str = f"* {instructions}" if instructions else ""
        guidelines_str = (
            ("\n\nGUIDELINES:\n" + length_str + instructions_str).strip("\n")
            if length or instructions
            else ""
        )
        input_prompt = f"""
Provide a response based on the query and findings below with as much detail as possible. {guidelines_str}

QUERY: {query}

FINDINGS:
{all_findings}
"""

        report = await self.writer_agent.write_report(
            query=query,
            findings=all_findings,
            output_length=length,
            output_instructions=instructions,
        )

        # Track tokens for final report (not per iteration, just total)
        estimated_tokens = self.budget_tracker.estimate_llm_call_tokens(input_prompt, report)
        self.budget_tracker.add_tokens(self.loop_id, estimated_tokens)
        self.logger.debug(
            "Tokens tracked for writer agent (final report)",
            tokens=estimated_tokens,
        )

        # Note: Citation validation for markdown reports would require Evidence objects
        # Currently, findings are strings, not Evidence objects. For full validation,
        # consider using ResearchReport format or passing Evidence objects separately.
        # See src/utils/citation_validator.py for markdown citation validation utilities.

        return report


class DeepResearchFlow:
    """
    Deep research flow that runs parallel iterative loops per section.

    Pattern: Plan → Parallel Iterative Loops (one per section) → Synthesis
    """

    def __init__(
        self,
        max_iterations: int = 5,
        max_time_minutes: int = 10,
        verbose: bool = True,
        use_long_writer: bool = True,
        use_graph: bool = False,
    ) -> None:
        """
        Initialize deep research flow.

        Args:
            max_iterations: Maximum iterations per section
            max_time_minutes: Maximum time per section
            verbose: Whether to log progress
            use_long_writer: Whether to use long writer (True) or proofreader (False)
            use_graph: Whether to use graph-based execution (True) or agent chains (False)
        """
        self.max_iterations = max_iterations
        self.max_time_minutes = max_time_minutes
        self.verbose = verbose
        self.use_long_writer = use_long_writer
        self.use_graph = use_graph
        self.logger = logger

        # Initialize agents (only needed for agent chain execution)
        if not use_graph:
            self.planner_agent = create_planner_agent()
            self.long_writer_agent = create_long_writer_agent()
            self.proofreader_agent = create_proofreader_agent()
            # Initialize judge handler for section loop completion
            self.judge_handler = create_judge_handler()
            # Initialize budget tracker for token tracking
            self.budget_tracker = BudgetTracker()
            self.loop_id = "deep_research_flow"
            self.budget_tracker.create_budget(
                loop_id=self.loop_id,
                tokens_limit=200000,  # Higher limit for deep research
                time_limit_seconds=max_time_minutes
                * 60
                * 2,  # Allow more time for parallel sections
                iterations_limit=max_iterations * 10,  # Allow for multiple sections
            )
            self.budget_tracker.start_timer(self.loop_id)

        # Graph orchestrator (lazy initialization)
        self._graph_orchestrator: Any = None

    async def run(self, query: str) -> str:
        """
        Run the deep research flow.

        Args:
            query: The research query

        Returns:
            Final report string
        """
        if self.use_graph:
            return await self._run_with_graph(query)
        else:
            return await self._run_with_chains(query)

    async def _run_with_chains(self, query: str) -> str:
        """
        Run the deep research flow using agent chains.

        Args:
            query: The research query

        Returns:
            Final report string
        """
        self.logger.info("Starting deep research (agent chains)", query=query[:100])

        # Initialize workflow state for deep research
        try:
            from src.services.embeddings import get_embedding_service

            embedding_service = get_embedding_service()
        except (ImportError, Exception):
            # If embedding service is unavailable, initialize without it
            embedding_service = None
            self.logger.debug("Embedding service unavailable, initializing state without it")

        init_workflow_state(embedding_service=embedding_service)
        self.logger.debug("Workflow state initialized for deep research")

        # 1. Build report plan
        report_plan = await self._build_report_plan(query)
        self.logger.info(
            "Report plan created",
            sections=len(report_plan.report_outline),
            title=report_plan.report_title,
        )

        # 2. Run parallel research loops with state synchronization
        section_drafts = await self._run_research_loops(report_plan)

        # Verify state synchronization - log evidence count
        state = get_workflow_state()
        self.logger.info(
            "State synchronization complete",
            total_evidence=len(state.evidence),
            sections_completed=len(section_drafts),
        )

        # 3. Create final report
        final_report = await self._create_final_report(query, report_plan, section_drafts)

        self.logger.info(
            "Deep research completed",
            sections=len(section_drafts),
            final_report_length=len(final_report),
        )

        return final_report

    async def _run_with_graph(self, query: str) -> str:
        """
        Run the deep research flow using graph execution.

        Args:
            query: The research query

        Returns:
            Final report string
        """
        self.logger.info("Starting deep research (graph execution)", query=query[:100])

        # Create graph orchestrator (lazy initialization)
        if self._graph_orchestrator is None:
            self._graph_orchestrator = create_graph_orchestrator(
                mode="deep",
                max_iterations=self.max_iterations,
                max_time_minutes=self.max_time_minutes,
                use_graph=True,
            )

        # Run orchestrator and collect events
        final_report = ""
        async for event in self._graph_orchestrator.run(query):
            if event.type == "complete":
                final_report = event.message
                break
            elif event.type == "error":
                self.logger.error("Graph execution error", error=event.message)
                raise RuntimeError(f"Graph execution failed: {event.message}")

        if not final_report:
            self.logger.warning("No complete event received from graph orchestrator")
            final_report = "Research completed but no report was generated."

        self.logger.info("Deep research completed (graph execution)")

        return final_report

    async def _build_report_plan(self, query: str) -> ReportPlan:
        """Build the initial report plan."""
        self.logger.info("Building report plan")

        # Build input prompt for token estimation
        input_prompt = f"QUERY: {query}"

        report_plan = await self.planner_agent.run(query)

        # Track tokens for planner agent
        if not self.use_graph and hasattr(self, "budget_tracker"):
            plan_text = (
                f"title={report_plan.report_title}, sections={len(report_plan.report_outline)}"
            )
            estimated_tokens = self.budget_tracker.estimate_llm_call_tokens(input_prompt, plan_text)
            self.budget_tracker.add_tokens(self.loop_id, estimated_tokens)
            self.logger.debug(
                "Tokens tracked for planner agent",
                tokens=estimated_tokens,
            )

        self.logger.info(
            "Report plan created",
            sections=len(report_plan.report_outline),
            has_background=bool(report_plan.background_context),
        )

        return report_plan

    async def _run_research_loops(self, report_plan: ReportPlan) -> list[str]:
        """Run parallel iterative research loops for each section."""
        self.logger.info("Running research loops", sections=len(report_plan.report_outline))

        # Create workflow manager for parallel execution
        workflow_manager = WorkflowManager()

        # Create loop configurations
        loop_configs = [
            {
                "loop_id": f"section_{i}",
                "query": section.key_question,
                "section_title": section.title,
                "background_context": report_plan.background_context,
            }
            for i, section in enumerate(report_plan.report_outline)
        ]

        async def run_research_for_section(config: dict[str, Any]) -> str:
            """Run iterative research for a single section."""
            loop_id = config.get("loop_id", "unknown")
            query = config.get("query", "")
            background_context = config.get("background_context", "")

            try:
                # Update loop status
                await workflow_manager.update_loop_status(loop_id, "running")

                # Create iterative research flow
                flow = IterativeResearchFlow(
                    max_iterations=self.max_iterations,
                    max_time_minutes=self.max_time_minutes,
                    verbose=self.verbose,
                    use_graph=self.use_graph,
                    judge_handler=self.judge_handler if not self.use_graph else None,
                )

                # Run research
                result = await flow.run(
                    query=query,
                    background_context=background_context,
                )

                # Sync evidence from flow to loop
                state = get_workflow_state()
                if state.evidence:
                    await workflow_manager.add_loop_evidence(loop_id, state.evidence)

                # Update loop status
                await workflow_manager.update_loop_status(loop_id, "completed")

                return result

            except Exception as e:
                error_msg = str(e)
                await workflow_manager.update_loop_status(loop_id, "failed", error=error_msg)
                self.logger.error(
                    "Section research failed",
                    loop_id=loop_id,
                    error=error_msg,
                )
                raise

        # Run all sections in parallel using workflow manager
        section_drafts = await workflow_manager.run_loops_parallel(
            loop_configs=loop_configs,
            loop_func=run_research_for_section,
            judge_handler=self.judge_handler if not self.use_graph else None,
            budget_tracker=self.budget_tracker if not self.use_graph else None,
        )

        # Sync evidence from all loops to global state
        for config in loop_configs:
            loop_id = config.get("loop_id")
            if loop_id:
                await workflow_manager.sync_loop_evidence_to_state(loop_id)

        # Filter out None results (failed loops)
        section_drafts = [draft for draft in section_drafts if draft is not None]

        self.logger.info(
            "Research loops completed",
            drafts=len(section_drafts),
            total_sections=len(report_plan.report_outline),
        )

        return section_drafts

    async def _create_final_report(
        self, query: str, report_plan: ReportPlan, section_drafts: list[str]
    ) -> str:
        """Create final report from section drafts."""
        self.logger.info("Creating final report")

        # Create ReportDraft from section drafts
        report_draft = ReportDraft(
            sections=[
                ReportDraftSection(
                    section_title=section.title,
                    section_content=draft,
                )
                for section, draft in zip(report_plan.report_outline, section_drafts, strict=False)
            ]
        )

        # Build input prompt for token estimation
        draft_text = "\n".join(
            [s.section_content[:500] for s in report_draft.sections[:5]]
        )  # Sample
        input_prompt = f"QUERY: {query}\nTITLE: {report_plan.report_title}\nDRAFT: {draft_text}"

        if self.use_long_writer:
            # Use long writer agent
            final_report = await self.long_writer_agent.write_report(
                original_query=query,
                report_title=report_plan.report_title,
                report_draft=report_draft,
            )
        else:
            # Use proofreader agent
            final_report = await self.proofreader_agent.proofread(
                query=query,
                report_draft=report_draft,
            )

        # Track tokens for final report synthesis
        if not self.use_graph and hasattr(self, "budget_tracker"):
            estimated_tokens = self.budget_tracker.estimate_llm_call_tokens(
                input_prompt, final_report
            )
            self.budget_tracker.add_tokens(self.loop_id, estimated_tokens)
            self.logger.debug(
                "Tokens tracked for final report synthesis",
                tokens=estimated_tokens,
                agent="long_writer" if self.use_long_writer else "proofreader",
            )

        self.logger.info("Final report created", length=len(final_report))

        return final_report
