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


async def run(query: str, *, verbose: bool = False) -> str:
    """Run the full graph and return the final briefing text."""
    if verbose:
        clear_tool_log()
    graph = build_graph()
    initial = {"query": query, "retries": 0, "findings": [], "missing": []}
    # recursion_limit is a backstop so a misbehaving loop can't run forever
    final = await graph.ainvoke(initial, config={"recursion_limit": 25})

    if verbose:
        for line in get_tool_log():
            print(line)

    if final.get("next_match"):
        print(f"NEXT MATCH: {final['next_match']}\n")
    return final.get("briefing") or "(no briefing produced)"


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