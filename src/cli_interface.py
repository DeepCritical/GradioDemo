"""CLI Interface for DeepCritical.

Provides a command-line interface to interact with the GraphOrchestrator,
supporting query refinement and real-time event streaming.
"""

import asyncio
import logging

import structlog
from dotenv import load_dotenv

from src.agent_factory.agents import create_graph_orchestrator
from src.utils.config import settings

# Configure simple logging for CLI
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)


async def run_research_cli() -> None:
    """Run the research CLI."""
    print("\n🔬 DeepCritical Research CLI")
    print("===========================\n")

    # Check for API keys
    if not (settings.has_openai_key or settings.has_anthropic_key or settings.hf_token):
        print("⚠️  Warning: No API keys found. Some features may be limited.")
        print("   Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, or HF_TOKEN in .env\n")

    while True:
        try:
            # Get user input
            query = input("\n🔎 Enter research query (or 'q' to quit): ").strip()

            if query.lower() in ("q", "quit", "exit"):
                print("Goodbye!")
                break

            if not query:
                continue

            print("\n🚀 Starting research process...")

            # Create orchestrator
            orchestrator = create_graph_orchestrator(mode="auto", use_graph=True)

            # Run and stream events
            final_report = ""
            async for event in orchestrator.run(query):
                # Print event with icon
                icons = {
                    "started": "🚦",
                    "searching": "🔍",
                    "search_complete": "✅",
                    "looping": "🔄",
                    "synthesizing": "📝",
                    "complete": "🎉",
                    "error": "❌",
                }
                icon = icons.get(event.type, "•")

                # Special handling for certain events
                if event.type == "started" and "Refined query" in event.message:
                    print(f"\n✨ {event.message}")
                    if event.data:
                        print(f"   Original: {event.data.get('original')}")
                elif event.type == "complete":
                    final_report = event.message
                    print(f"\n{icon} Research Complete!")
                elif event.type == "error":
                    print(f"\n{icon} Error: {event.message}")
                else:
                    print(f"{icon} {event.message}")

            # Print final report
            if final_report:
                print("\n" + "=" * 80)
                print("FINAL REPORT")
                print("=" * 80 + "\n")
                print(final_report)
                print("\n" + "=" * 80 + "\n")

        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback

            traceback.print_exc()


def main() -> None:
    """Entry point."""
    load_dotenv()
    try:
        asyncio.run(run_research_cli())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
