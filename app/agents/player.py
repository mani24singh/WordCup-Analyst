"""Step 8 — Player scout agent node.

Uses get_top_scorers then optionally get_player_profile. The prompt rule about
not naming a rival player exists because a naive picker would fall back to the
tournament's overall top scorer under the wrong heading.
"""

from app.agents.runner import run_agent_finding
from app.agents.tools import player_tools

_SYSTEM = (
    "You are a player scout. Use get_top_scorers to find the FOCUS TEAM's leading "
    "scorer, then optionally use get_player_profile to add their position/club. "
    "Write 2-3 sentences scouting that player. If the focus team has NO scorer "
    "yet, say so plainly and do NOT name a player from another team."
)


async def player_node(state):
    """LangGraph node: scout the focus team's key player for the next match."""
    team = state.get("team_name") or "the focus team"
    task = f"Identify and scout {team}'s key player for their next match."
    return await run_agent_finding(
        "player_agent",
        "Key Player",
        player_tools(state),
        _SYSTEM,
        task,
    )