"""Step 8 — News agent node.

Gathers injuries, lineup doubts, and storylines from RSS (always free) and Tavily
(when configured). Answers what just happened that the numbers don't show.
"""

from app.agents.runner import run_agent_finding
from app.agents.tools import news_tools

_SYSTEM = (
    "You are a football news analyst. Use fetch_rss_headlines and search_team_news "
    "to gather injuries, lineup doubts, and storylines. "
    "Write a concise News & Storylines section in 3-5 bullet points."
)


async def news_node(state):
    """LangGraph node: latest news and narrative context for the fixture."""
    team = state.get("team_name") or "the focus team"
    opponent = state.get("opponent_name") or "their opponent"
    task = f"Gather latest news and storylines for {team} ahead of their match vs {opponent}."
    return await run_agent_finding(
        "news_agent",
        "News & Storylines",
        news_tools(state),
        _SYSTEM,
        task,
    )