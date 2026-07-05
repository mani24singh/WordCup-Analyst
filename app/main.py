"""Step 12 — CLI entry point.

Ties the graph to the terminal. ``--verbose`` prints each agent's tool calls as
proof that workers chose their own tools in parallel.

Usage::

    PYTHONPATH=. uv run python app/main.py "Give me a briefing on Brazil's next match"
    PYTHONPATH=. uv run python app/main.py "Brief me on France's next match" --verbose
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.runner import clear_tool_log, get_tool_log
from app.graph import build_graph


async def run_briefing(query: str, *, verbose: bool = False) -> dict:
    """Run the full graph and return structured briefing output."""
    if verbose:
        clear_tool_log()
    graph = build_graph()
    initial = {"query": query, "retries": 0, "findings": [], "missing": []}
    final = await graph.ainvoke(initial, config={"recursion_limit": 25})

    if verbose:
        for line in get_tool_log():
            print(line)

    return {
        "query": query,
        "team_name": final.get("team_name"),
        "team_name_input": final.get("team_name_input"),
        "team_name_corrected": final.get("team_name_corrected", False),
        "team_resolve_error": final.get("team_resolve_error"),
        "next_match": final.get("next_match"),
        "briefing": final.get("briefing") or "(no briefing produced)",
        "tool_log": list(get_tool_log()) if verbose else [],
    }


async def run(query: str, *, verbose: bool = False) -> str:
    """Run the full graph and return the final briefing text."""
    result = await run_briefing(query, verbose=verbose)
    if result.get("next_match"):
        print(f"NEXT MATCH: {result['next_match']}\n")
    return result["briefing"]


def main() -> None:
    """Parse CLI args and print the match-day briefing."""
    parser = argparse.ArgumentParser(description="World Cup match-day briefing")
    parser.add_argument("query", help='e.g. "Give me a briefing on Brazil\'s next match"')
    parser.add_argument("--verbose", action="store_true", help="Show agent tool calls")
    args = parser.parse_args()

    briefing = asyncio.run(run(args.query, verbose=args.verbose))
    print(briefing)


if __name__ == "__main__":
    main()