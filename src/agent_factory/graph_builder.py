"""Graph builder utilities for constructing research workflow graphs.

Provides classes and utilities for building graph-based orchestration systems
using Pydantic AI agents as nodes.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

import structlog
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pydantic_ai import Agent

    from src.middleware.state_machine import WorkflowState

logger = structlog.get_logger()


# ============================================================================
# Graph Node Models
# ============================================================================


class GraphNode(BaseModel):
    """Base class for graph nodes."""

    node_id: str = Field(description="Unique identifier for the node")
    node_type: Literal["agent", "state", "decision", "parallel"] = Field(description="Type of node")
    description: str = Field(default="", description="Human-readable description of the node")

    model_config = {"frozen": True}


class AgentNode(GraphNode):
    """Node that executes a Pydantic AI agent."""

    node_type: Literal["agent"] = "agent"
    agent: Any = Field(description="Pydantic AI agent to execute")
    input_transformer: Callable[[Any], Any] | None = Field(
        default=None, description="Transform input before passing to agent"
    )
    output_transformer: Callable[[Any], Any] | None = Field(
        default=None, description="Transform output after agent execution"
    )

    model_config = {"arbitrary_types_allowed": True}


class StateNode(GraphNode):
    """Node that updates or reads workflow state."""

    node_type: Literal["state"] = "state"
    state_updater: Callable[[Any, Any], Any] = Field(
        description="Function to update workflow state"
    )
    state_reader: Callable[[Any], Any] | None = Field(
        default=None, description="Function to read state (optional)"
    )

    model_config = {"arbitrary_types_allowed": True}


class DecisionNode(GraphNode):
    """Node that makes routing decisions based on conditions."""

    node_type: Literal["decision"] = "decision"
    decision_function: Callable[[Any], str] = Field(
        description="Function that returns next node ID based on input"
    )
    options: list[str] = Field(description="List of possible next node IDs", min_length=1)

    model_config = {"arbitrary_types_allowed": True}


class ParallelNode(GraphNode):
    """Node that executes multiple nodes in parallel."""

    node_type: Literal["parallel"] = "parallel"
    parallel_nodes: list[str] = Field(
        description="List of node IDs to run in parallel", min_length=0
    )
    aggregator: Callable[[list[Any]], Any] | None = Field(
        default=None, description="Function to aggregate parallel results"
    )

    model_config = {"arbitrary_types_allowed": True}


# ============================================================================
# Graph Edge Models
# ============================================================================


class GraphEdge(BaseModel):
    """Base class for graph edges."""

    from_node: str = Field(description="Source node ID")
    to_node: str = Field(description="Target node ID")
    condition: Callable[[Any], bool] | None = Field(
        default=None, description="Optional condition function"
    )
    weight: float = Field(default=1.0, description="Edge weight for routing decisions")

    model_config = {"arbitrary_types_allowed": True}


class SequentialEdge(GraphEdge):
    """Edge that is always traversed (no condition)."""

    condition: None = None


class ConditionalEdge(GraphEdge):
    """Edge that is traversed based on a condition."""

    condition: Callable[[Any], bool] = Field(description="Required condition function")
    condition_description: str = Field(
        default="", description="Human-readable description of condition"
    )


class ParallelEdge(GraphEdge):
    """Edge used for parallel execution branches."""

    condition: None = None


# ============================================================================
# Research Graph Class
# ============================================================================


class ResearchGraph(BaseModel):
    """Represents a research workflow graph with nodes and edges."""

    nodes: dict[str, GraphNode] = Field(default_factory=dict, description="All nodes in the graph")
    edges: dict[str, list[GraphEdge]] = Field(
        default_factory=dict, description="Edges by source node ID"
    )
    entry_node: str = Field(description="Starting node ID")
    exit_nodes: list[str] = Field(default_factory=list, description="Terminal node IDs")

    model_config = {"arbitrary_types_allowed": True}

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph.

        Args:
            node: The node to add

        Raises:
            ValueError: If node ID already exists
        """
        if node.node_id in self.nodes:
            raise ValueError(f"Node {node.node_id} already exists in graph")
        self.nodes[node.node_id] = node
        logger.debug("Node added to graph", node_id=node.node_id, type=node.node_type)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph.

        Args:
            edge: The edge to add

        Raises:
            ValueError: If source or target node doesn't exist
        """
        if edge.from_node not in self.nodes:
            raise ValueError(f"Source node {edge.from_node} not found in graph")
        if edge.to_node not in self.nodes:
            raise ValueError(f"Target node {edge.to_node} not found in graph")

        if edge.from_node not in self.edges:
            self.edges[edge.from_node] = []
        self.edges[edge.from_node].append(edge)
        logger.debug(
            "Edge added to graph",
            from_node=edge.from_node,
            to_node=edge.to_node,
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID.

        Args:
            node_id: The node ID

        Returns:
            The node, or None if not found
        """
        return self.nodes.get(node_id)

    def get_next_nodes(self, node_id: str, context: Any = None) -> list[tuple[str, GraphEdge]]:
        """Get all possible next nodes from a given node.

        Args:
            node_id: The current node ID
            context: Optional context for evaluating conditions

        Returns:
            List of (node_id, edge) tuples for valid next nodes
        """
        if node_id not in self.edges:
            return []

        next_nodes = []
        for edge in self.edges[node_id]:
            # Evaluate condition if present
            if edge.condition is None or edge.condition(context):
                next_nodes.append((edge.to_node, edge))

        return next_nodes

    def validate_structure(self) -> list[str]:
        """Validate the graph structure.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check entry node exists
        if self.entry_node not in self.nodes:
            errors.append(f"Entry node {self.entry_node} not found in graph")

        # Check exit nodes exist and at least one is defined
        if not self.exit_nodes:
            errors.append("At least one exit node must be defined")
        for exit_node in self.exit_nodes:
            if exit_node not in self.nodes:
                errors.append(f"Exit node {exit_node} not found in graph")

        # Check all edges reference valid nodes
        for from_node, edge_list in self.edges.items():
            if from_node not in self.nodes:
                errors.append(f"Edge source node {from_node} not found")
            for edge in edge_list:
                if edge.to_node not in self.nodes:
                    errors.append(f"Edge target node {edge.to_node} not found")

        # Check all nodes are reachable from entry node (basic check)
        if self.entry_node in self.nodes:
            reachable = {self.entry_node}
            queue = [self.entry_node]
            while queue:
                current = queue.pop(0)
                for next_node, _ in self.get_next_nodes(current):
                    if next_node not in reachable:
                        reachable.add(next_node)
                        queue.append(next_node)

            unreachable = set(self.nodes.keys()) - reachable
            if unreachable:
                errors.append(f"Unreachable nodes from entry node: {', '.join(unreachable)}")

        return errors


# ============================================================================
# Graph Builder Class
# ============================================================================


class GraphBuilder:
    """Builder for constructing research workflow graphs."""

    def __init__(self) -> None:
        """Initialize the graph builder."""
        self.graph = ResearchGraph(entry_node="", exit_nodes=[])

    def add_agent_node(
        self,
        node_id: str,
        agent: "Agent[Any, Any]",
        description: str = "",
        input_transformer: Callable[[Any], Any] | None = None,
        output_transformer: Callable[[Any], Any] | None = None,
    ) -> "GraphBuilder":
        """Add an agent node to the graph.

        Args:
            node_id: Unique identifier for the node
            agent: Pydantic AI agent to execute
            description: Human-readable description
            input_transformer: Optional input transformation function
            output_transformer: Optional output transformation function

        Returns:
            Self for method chaining
        """
        node = AgentNode(
            node_id=node_id,
            agent=agent,
            description=description,
            input_transformer=input_transformer,
            output_transformer=output_transformer,
        )
        self.graph.add_node(node)
        return self

    def add_state_node(
        self,
        node_id: str,
        state_updater: Callable[["WorkflowState", Any], "WorkflowState"],
        description: str = "",
        state_reader: Callable[["WorkflowState"], Any] | None = None,
    ) -> "GraphBuilder":
        """Add a state node to the graph.

        Args:
            node_id: Unique identifier for the node
            state_updater: Function to update workflow state
            description: Human-readable description
            state_reader: Optional function to read state

        Returns:
            Self for method chaining
        """
        node = StateNode(
            node_id=node_id,
            state_updater=state_updater,
            description=description,
            state_reader=state_reader,
        )
        self.graph.add_node(node)
        return self

    def add_decision_node(
        self,
        node_id: str,
        decision_function: Callable[[Any], str],
        options: list[str],
        description: str = "",
    ) -> "GraphBuilder":
        """Add a decision node to the graph.

        Args:
            node_id: Unique identifier for the node
            decision_function: Function that returns next node ID
            options: List of possible next node IDs
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        node = DecisionNode(
            node_id=node_id,
            decision_function=decision_function,
            options=options,
            description=description,
        )
        self.graph.add_node(node)
        return self

    def add_parallel_node(
        self,
        node_id: str,
        parallel_nodes: list[str],
        description: str = "",
        aggregator: Callable[[list[Any]], Any] | None = None,
    ) -> "GraphBuilder":
        """Add a parallel node to the graph.

        Args:
            node_id: Unique identifier for the node
            parallel_nodes: List of node IDs to run in parallel
            description: Human-readable description
            aggregator: Optional function to aggregate results

        Returns:
            Self for method chaining
        """
        node = ParallelNode(
            node_id=node_id,
            parallel_nodes=parallel_nodes,
            description=description,
            aggregator=aggregator,
        )
        self.graph.add_node(node)
        return self

    def connect_nodes(
        self,
        from_node: str,
        to_node: str,
        condition: Callable[[Any], bool] | None = None,
        condition_description: str = "",
    ) -> "GraphBuilder":
        """Connect two nodes with an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            condition: Optional condition function
            condition_description: Description of condition (if conditional)

        Returns:
            Self for method chaining
        """
        if condition is None:
            edge: GraphEdge = SequentialEdge(from_node=from_node, to_node=to_node)
        else:
            edge = ConditionalEdge(
                from_node=from_node,
                to_node=to_node,
                condition=condition,
                condition_description=condition_description,
            )
        self.graph.add_edge(edge)
        return self

    def set_entry_node(self, node_id: str) -> "GraphBuilder":
        """Set the entry node for the graph.

        Args:
            node_id: The entry node ID

        Returns:
            Self for method chaining
        """
        self.graph.entry_node = node_id
        return self

    def set_exit_nodes(self, node_ids: list[str]) -> "GraphBuilder":
        """Set the exit nodes for the graph.

        Args:
            node_ids: List of exit node IDs

        Returns:
            Self for method chaining
        """
        self.graph.exit_nodes = node_ids
        return self

    def build(self) -> ResearchGraph:
        """Finalize graph construction and validate.

        Returns:
            The constructed ResearchGraph

        Raises:
            ValueError: If graph validation fails
        """
        errors = self.graph.validate_structure()
        if errors:
            error_msg = "Graph validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error("Graph validation failed", errors=errors)
            raise ValueError(error_msg)

        logger.info(
            "Graph built successfully",
            nodes=len(self.graph.nodes),
            edges=sum(len(edges) for edges in self.graph.edges.values()),
            entry_node=self.graph.entry_node,
            exit_nodes=self.graph.exit_nodes,
        )
        return self.graph


# ============================================================================
# Factory Functions
# ============================================================================


def create_iterative_graph(
    knowledge_gap_agent: "Agent[Any, Any]",
    tool_selector_agent: "Agent[Any, Any]",
    thinking_agent: "Agent[Any, Any]",
    writer_agent: "Agent[Any, Any]",
) -> ResearchGraph:
    """Create a graph for iterative research flow.

    Args:
        knowledge_gap_agent: Agent for evaluating knowledge gaps
        tool_selector_agent: Agent for selecting tools
        thinking_agent: Agent for generating observations
        writer_agent: Agent for writing final report

    Returns:
        Constructed ResearchGraph for iterative research
    """
    builder = GraphBuilder()

    # Add nodes
    builder.add_agent_node("thinking", thinking_agent, "Generate observations")
    builder.add_agent_node("knowledge_gap", knowledge_gap_agent, "Evaluate knowledge gaps")
    builder.add_decision_node(
        "continue_decision",
        decision_function=lambda result: "writer"
        if getattr(result, "research_complete", False)
        else "tool_selector",
        options=["tool_selector", "writer"],
        description="Decide whether to continue research or write report",
    )
    builder.add_agent_node("tool_selector", tool_selector_agent, "Select tools to address gap")
    builder.add_state_node(
        "execute_tools",
        state_updater=lambda state,
        tasks: state,  # Placeholder - actual execution handled separately
        description="Execute selected tools",
    )
    builder.add_agent_node("writer", writer_agent, "Write final report")

    # Add edges
    builder.connect_nodes("thinking", "knowledge_gap")
    builder.connect_nodes("knowledge_gap", "continue_decision")
    builder.connect_nodes("continue_decision", "tool_selector")
    builder.connect_nodes("continue_decision", "writer")
    builder.connect_nodes("tool_selector", "execute_tools")
    builder.connect_nodes("execute_tools", "thinking")  # Loop back

    # Set entry and exit
    builder.set_entry_node("thinking")
    builder.set_exit_nodes(["writer"])

    return builder.build()


def create_deep_graph(
    planner_agent: "Agent[Any, Any]",
    knowledge_gap_agent: "Agent[Any, Any]",
    tool_selector_agent: "Agent[Any, Any]",
    thinking_agent: "Agent[Any, Any]",
    writer_agent: "Agent[Any, Any]",
    long_writer_agent: "Agent[Any, Any]",
) -> ResearchGraph:
    """Create a graph for deep research flow.

    The graph structure: planner → store_plan → parallel_loops → collect_drafts → synthesizer

    Args:
        planner_agent: Agent for creating report plan
        knowledge_gap_agent: Agent for evaluating knowledge gaps (not used directly, but needed for iterative flows)
        tool_selector_agent: Agent for selecting tools (not used directly, but needed for iterative flows)
        thinking_agent: Agent for generating observations (not used directly, but needed for iterative flows)
        writer_agent: Agent for writing section reports (not used directly, but needed for iterative flows)
        long_writer_agent: Agent for synthesizing final report

    Returns:
        Constructed ResearchGraph for deep research
    """
    from src.utils.models import ReportPlan

    builder = GraphBuilder()

    # Add nodes
    # 1. Planner agent - creates report plan
    builder.add_agent_node("planner", planner_agent, "Create report plan with sections")

    # 2. State node - store report plan in workflow state
    def store_plan(state: "WorkflowState", plan: ReportPlan) -> "WorkflowState":
        """Store report plan in state for parallel loops to access."""
        # Store plan in a custom attribute (we'll need to extend WorkflowState or use a dict)
        # For now, we'll store it in the context's node_results
        # The actual storage will happen in the graph execution
        return state

    builder.add_state_node(
        "store_plan",
        state_updater=store_plan,
        description="Store report plan in state",
    )

    # 3. Parallel node - will execute iterative research flows for each section
    # The actual execution will be handled dynamically in _execute_parallel_node()
    # We use a special node ID that the executor will recognize
    builder.add_parallel_node(
        "parallel_loops",
        parallel_nodes=[],  # Will be populated dynamically based on report plan
        description="Execute parallel iterative research loops for each section",
        aggregator=lambda results: results,  # Collect all section drafts
    )

    # 4. State node - collect section drafts into ReportDraft
    def collect_drafts(state: "WorkflowState", section_drafts: list[str]) -> "WorkflowState":
        """Collect section drafts into state for synthesizer."""
        # Store drafts in state (will be accessed by synthesizer)
        return state

    builder.add_state_node(
        "collect_drafts",
        state_updater=collect_drafts,
        description="Collect section drafts for synthesis",
    )

    # 5. Synthesizer agent - creates final report from drafts
    builder.add_agent_node(
        "synthesizer", long_writer_agent, "Synthesize final report from section drafts"
    )

    # Add edges
    builder.connect_nodes("planner", "store_plan")
    builder.connect_nodes("store_plan", "parallel_loops")
    builder.connect_nodes("parallel_loops", "collect_drafts")
    builder.connect_nodes("collect_drafts", "synthesizer")

    # Set entry and exit
    builder.set_entry_node("planner")
    builder.set_exit_nodes(["synthesizer"])

    return builder.build()


# No need to rebuild models since we're using Any types
# The models will work correctly with arbitrary_types_allowed=True
