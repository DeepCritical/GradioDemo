"""Tool executor for running AgentTask objects.

Executes tool tasks selected by the tool selector agent and returns ToolAgentOutput.
"""

import structlog

from src.tools.crawl_adapter import crawl_website
from src.tools.rag_tool import RAGTool, create_rag_tool
from src.tools.web_search_adapter import web_search
from src.utils.exceptions import ConfigurationError
from src.utils.models import AgentTask, Evidence, ToolAgentOutput

logger = structlog.get_logger()

# Module-level RAG tool instance (lazy initialization)
_rag_tool: RAGTool | None = None


def _get_rag_tool() -> RAGTool | None:
    """
    Get or create RAG tool instance.

    Returns:
        RAGTool instance, or None if unavailable
    """
    global _rag_tool
    if _rag_tool is None:
        try:
            _rag_tool = create_rag_tool()
            logger.info("RAG tool initialized")
        except ConfigurationError:
            logger.warning("RAG tool unavailable (OPENAI_API_KEY required)")
            return None
        except Exception as e:
            logger.error("Failed to initialize RAG tool", error=str(e))
            return None
    return _rag_tool


def _evidence_to_text(evidence_list: list[Evidence]) -> str:
    """
    Convert Evidence objects to formatted text.

    Args:
        evidence_list: List of Evidence objects

    Returns:
        Formatted text string with citations and content
    """
    if not evidence_list:
        return "No evidence found."

    formatted_parts = []
    for i, evidence in enumerate(evidence_list, 1):
        citation = evidence.citation
        citation_str = f"{citation.formatted}"
        if citation.url:
            citation_str += f" [{citation.url}]"

        formatted_parts.append(f"[{i}] {citation_str}\n\n{evidence.content}\n\n---\n")

    return "\n".join(formatted_parts)


async def execute_agent_task(task: AgentTask) -> ToolAgentOutput:
    """
    Execute a single agent task and return ToolAgentOutput.

    Args:
        task: AgentTask specifying which tool to use and what query to run

    Returns:
        ToolAgentOutput with results and source URLs
    """
    logger.info(
        "Executing agent task",
        agent=task.agent,
        query=task.query[:100] if task.query else "",
        gap=task.gap[:100] if task.gap else "",
    )

    try:
        if task.agent == "WebSearchAgent":
            # Use web search adapter
            result_text = await web_search(task.query)
            # Extract URLs from result (simple heuristic - look for http/https)
            import re

            urls = re.findall(r"https?://[^\s\)]+", result_text)
            sources = list(set(urls))  # Deduplicate

            return ToolAgentOutput(output=result_text, sources=sources)

        elif task.agent == "SiteCrawlerAgent":
            # Use crawl adapter
            if task.entity_website:
                starting_url = task.entity_website
            elif task.query.startswith(("http://", "https://")):
                starting_url = task.query
            else:
                # Try to construct URL from query
                starting_url = f"https://{task.query}"

            result_text = await crawl_website(starting_url)
            # Extract URLs from result
            import re

            urls = re.findall(r"https?://[^\s\)]+", result_text)
            sources = list(set(urls))  # Deduplicate

            return ToolAgentOutput(output=result_text, sources=sources)

        elif task.agent == "RAGAgent":
            # Use RAG tool for semantic search
            rag_tool = _get_rag_tool()
            if rag_tool is None:
                return ToolAgentOutput(
                    output="RAG service unavailable. OPENAI_API_KEY required.",
                    sources=[],
                )

            # Search RAG and get Evidence objects
            evidence_list = await rag_tool.search(task.query, max_results=10)

            if not evidence_list:
                return ToolAgentOutput(
                    output="No relevant evidence found in collected research.",
                    sources=[],
                )

            # Convert Evidence to formatted text
            result_text = _evidence_to_text(evidence_list)

            # Extract URLs from evidence citations
            sources = [evidence.citation.url for evidence in evidence_list if evidence.citation.url]

            return ToolAgentOutput(output=result_text, sources=sources)

        else:
            logger.warning("Unknown agent type", agent=task.agent)
            return ToolAgentOutput(
                output=f"Unknown agent type: {task.agent}. Available: WebSearchAgent, SiteCrawlerAgent, RAGAgent",
                sources=[],
            )

    except Exception as e:
        logger.error("Tool execution failed", error=str(e), agent=task.agent)
        return ToolAgentOutput(
            output=f"Error executing {task.agent} for gap '{task.gap}': {e!s}",
            sources=[],
        )


async def execute_tool_tasks(
    tasks: list[AgentTask],
) -> dict[str, ToolAgentOutput]:
    """
    Execute multiple agent tasks concurrently.

    Args:
        tasks: List of AgentTask objects to execute

    Returns:
        Dictionary mapping task keys to ToolAgentOutput results
    """
    import asyncio

    logger.info("Executing tool tasks", count=len(tasks))

    # Create async tasks
    async_tasks = [execute_agent_task(task) for task in tasks]

    # Run concurrently
    results_list = await asyncio.gather(*async_tasks, return_exceptions=True)

    # Build results dictionary
    results: dict[str, ToolAgentOutput] = {}
    for i, (task, result) in enumerate(zip(tasks, results_list, strict=False)):
        if isinstance(result, Exception):
            logger.error("Task execution failed", error=str(result), task_index=i)
            results[f"{task.agent}_{i}"] = ToolAgentOutput(output=f"Error: {result!s}", sources=[])
        else:
            # Type narrowing: result is ToolAgentOutput after Exception check
            assert isinstance(
                result, ToolAgentOutput
            ), "Expected ToolAgentOutput after Exception check"
            key = f"{task.agent}_{task.gap or i}" if task.gap else f"{task.agent}_{i}"
            results[key] = result

    logger.info("Tool tasks completed", completed=len(results))

    return results
