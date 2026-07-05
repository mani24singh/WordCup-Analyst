"""Step 8 — Matchup agent node.

Compares focus team vs opponent form and group standings using tools that already
know both team ids from supervisor-resolved state.
"""

from app.agents.runner import run_agent_finding
from app.agents.tools import matchup_tools

_SYSTEM = (
    "You are a matchup analyst. Compare the focus team and opponent using "
    "get_team_form, get_opponent_form, and get_group_standings. "
    "Write a concise Form & Matchup section in 3-5 bullet points."
)


async def matchup_node(state):
    """LangGraph node: form and standings comparison for the upcoming fixture."""
    team = state.get("team_name") or "the focus team"
    opponent = state.get("opponent_name") or "their opponent"
    task = f"Compare {team} vs {opponent} form and group standings for their next match."
    return await run_agent_finding(
        "matchup_agent",
        "Form & Matchup",
        matchup_tools(state),
        _SYSTEM,
        task,
    )