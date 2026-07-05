"""Step 9 — Supervisor (router) node.

Reads the question once, picks which agents to run, and resolves shared context
(team id, opponent, next fixture) so the three agents don't each repeat that
lookup. ``with_structured_output`` forces a typed routing object instead of messy
free text. Deterministic guardrails keep routing reliable when the LLM omits agents.
"""

import re

from pydantic import BaseModel, Field

from app.agents.runner import ainvoke_with_backoff
from app.config import light_model
from app.data.client import FootballDataClient

ALL_JOBS = ["matchup_agent", "player_agent", "news_agent"]

_SYSTEM = (
    "You route World Cup briefing questions. "
    "Extract the focus team_name and which agents to run. "
    "Valid agents: matchup_agent, player_agent, news_agent."
)


class _Route(BaseModel):
    """Structured routing decision returned by the supervisor LLM."""

    team_name: str | None = Field(default=None, description="Focus team, else null")
    jobs: list[str] = Field(default_factory=list, description="Agents to run")


def _fallback_route(query: str) -> _Route:
    """Regex fallback when Groq structured output fails on longer queries."""
    team = None
    for pattern in (
        r"briefing on ([^']+)'s",
        r"brief me on (\w+)",
        r"on (\w+)'s next",
        r"(\w+)'s next match",
    ):
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            team = match.group(1).strip()
            break
    jobs = ["player_agent"] if "scorer" in query.lower() else ALL_JOBS.copy()
    return _Route(team_name=team, jobs=jobs)


async def _route_query(query: str) -> _Route:
    """Ask the 8b router which team and agents to run."""
    router = light_model().with_structured_output(_Route, method="function_calling")
    try:
        return await ainvoke_with_backoff(
            router,
            [("system", _SYSTEM), ("human", query)],
            retries=1,
        )
    except Exception:
        return _fallback_route(query)


async def _resolve_context(team: str) -> dict:
    """Resolve team id, opponent, and next fixture once for all downstream agents."""
    async with FootballDataClient() as client:
        resolved = await client.resolve_team_id(team)
        if not resolved.ok or not resolved.data:
            return {}
        fixture = await client.next_match(resolved.data.id)

    if not fixture.ok or not fixture.data:
        return {
            "team_name": team,
            "team_id": resolved.data.id,
            "next_match": None,
        }

    match = fixture.data
    home = match.home_team
    away = match.away_team
    if home.id == resolved.data.id:
        opponent = away
    else:
        opponent = home
    date_str = (match.utc_date or "")[:10]
    next_match = f"{home.name} vs {away.name} - {date_str}"

    # store team_id, opponent_name, opponent_id, next_match in the returned dict
    return {
        "team_name": team,
        "team_id": resolved.data.id,
        "opponent_name": opponent.name,
        "opponent_id": opponent.id,
        "next_match": next_match,
    }


def _apply_guardrails(team_name: str | None, jobs: list[str]) -> list[str]:
    """Hard rules: if a team is named, always run matchup and news agents."""
    chosen = [j for j in jobs if j in ALL_JOBS]
    if team_name:
        for required in ("matchup_agent", "news_agent"):
            if required not in chosen:
                chosen.append(required)
        if not chosen:
            chosen = ALL_JOBS.copy()
    return chosen or ALL_JOBS.copy()


async def supervisor_node(state):
    """LangGraph entry node: route the query and fill shared match context."""
    query = state.get("query", "")
    decision = await _route_query(query)

    team_name = decision.team_name
    jobs = _apply_guardrails(team_name, decision.jobs)

    update: dict = {"jobs": jobs}
    if team_name:
        update.update(await _resolve_context(team_name))
    else:
        update["team_name"] = None

    return update