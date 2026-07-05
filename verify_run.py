"""End-to-end workflow verification — full supervisor → agents → synthesizer pipeline.

Run::

    uv run python verify_run.py
    uv run python verify_run.py "Give me a briefing on Brazil's next match"
    uv run python verify_run.py "Brief me on France's next match" --verbose

Exits 0 on pass, 1 on failure. Checks keys, graph output, and all three agent findings.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agents.runner import clear_tool_log, get_tool_log
from app.agents.synthesizer import latest_findings
from app.config import SETTINGS
from app.graph import build_graph

DEFAULT_QUERY = "Give me a briefing on Brazil's next match"
REQUIRED_AGENTS = {"matchup_agent", "player_agent", "news_agent"}


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return ok


async def verify(query: str, *, verbose: bool = False) -> bool:
    """Run the full graph and assert the workflow produced a valid briefing."""
    print("WordCup-Analyst — end-to-end verification\n")

    results: list[bool] = []

    results.append(_check("GROQ_API_KEY set", bool(SETTINGS.groq_api_key)))
    results.append(_check("FOOTBALL_DATA_TOKEN set", bool(SETTINGS.football_token)))
    if SETTINGS.has_tavily:
        print("  [info] TAVILY_API_KEY set — news agent can use web search")
    else:
        print("  [info] TAVILY_API_KEY not set — news agent uses RSS only")

    print(f"\nQuery: {query!r}\nRunning graph...")

    if verbose:
        clear_tool_log()

    graph = build_graph()
    final = await graph.ainvoke(
        {"query": query, "retries": 0, "findings": [], "missing": []},
        config={"recursion_limit": 25},
    )

    if verbose:
        print("\nTool calls:")
        for line in get_tool_log():
            print(f"  {line}")

    print("\nResults:")
    results.append(_check("team resolved", bool(final.get("team_name")), final.get("team_name", "")))
    results.append(_check("next match found", bool(final.get("next_match")), final.get("next_match", "")))

    briefing = final.get("briefing") or ""
    results.append(
        _check(
            "briefing produced",
            bool(briefing) and briefing != "(no briefing produced)",
            f"{len(briefing)} chars",
        )
    )

    findings = latest_findings(final.get("findings") or [])
    agents_seen = {f.agent for f in findings}
    results.append(
        _check(
            "all three agents ran",
            REQUIRED_AGENTS.issubset(agents_seen),
            ", ".join(sorted(agents_seen)) or "none",
        )
    )
    for finding in findings:
        results.append(
            _check(
                f"{finding.agent} returned content",
                bool(finding.content.strip()),
                finding.title,
            )
        )

    print("\n--- NEXT MATCH ---")
    print(final.get("next_match") or "(none)")
    print("\n--- BRIEFING (preview) ---")
    preview = briefing[:600] + ("..." if len(briefing) > 600 else "")
    print(preview)

    passed = all(results)
    print(f"\n{'VERIFICATION PASSED' if passed else 'VERIFICATION FAILED'}")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the complete WordCup-Analyst workflow")
    parser.add_argument(
        "query",
        nargs="?",
        default=DEFAULT_QUERY,
        help=f'Briefing query (default: "{DEFAULT_QUERY}")',
    )
    parser.add_argument("--verbose", action="store_true", help="Print agent tool calls")
    args = parser.parse_args()

    ok = asyncio.run(verify(args.query, verbose=args.verbose))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()