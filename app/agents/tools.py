"""Step 6 — Tool factories that give agents hands.

Tools are plain Python functions the model may call. Factories close over
``team_id`` / ``opponent_id`` from state so the model never has to invent ids.
Each tool returns a compact string (not giant JSON) to save Groq tokens.
"""

from langchain_core.tools import BaseTool, tool

from app.data.client import FootballDataClient
from app.data.models import Match
from app.data.news import NewsClient
from app.data.sportsdb import SportsDbClient


def _result_for_team(match: Match, team_id: int) -> str:
    """Single-match W/D/L letter for the focus team."""
    hs = match.score.full_time.home
    aws = match.score.full_time.away
    if hs is None or aws is None:
        return "?"
    if match.home_team.id == team_id:
        if hs > aws:
            return "W"
        if hs < aws:
            return "L"
        return "D"
    if match.away_team.id == team_id:
        if aws > hs:
            return "W"
        if aws < hs:
            return "L"
        return "D"
    return "?"


def _form_str(label: str, team_id: int, matches: list[Match]) -> str:
    """Compact form string handed back to the matchup agent."""
    form = "".join(_result_for_team(m, team_id) for m in matches)
    lines = []
    for m in matches:
        hs = m.score.full_time.home
        aws = m.score.full_time.away
        lines.append(f"{m.home_team.name} {hs}-{aws} {m.away_team.name}")
    return f"{label} form ({form}): " + "; ".join(lines)


def matchup_tools(state) -> list[BaseTool]:
    """Tools for form comparison and group standings (ids baked in from state)."""
    team_id = state.get("team_id")
    opp_id = state.get("opponent_id")

    @tool
    async def get_team_form() -> str:
        """Get the focus team's last-5 World Cup results and W/D/L form."""
        async with FootballDataClient() as c:
            r = await c.team_form(team_id, 5)
        if not r.ok or not r.data:
            return "form unavailable."
        return _form_str("the team", team_id, r.data)

    @tool
    async def get_opponent_form() -> str:
        """Get the opponent's last-5 World Cup results and W/D/L form."""
        async with FootballDataClient() as c:
            r = await c.team_form(opp_id, 5)
        if not r.ok or not r.data:
            return "form unavailable."
        return _form_str("the opponent", opp_id, r.data)

    @tool
    async def get_group_standings() -> str:
        """Get World Cup group standings for the focus team and opponent."""
        async with FootballDataClient() as c:
            r = await c.standings()
        if not r.ok or not r.data:
            return "standings unavailable."
        chunks = []
        for group in r.data:
            rows = []
            for row in group.table:
                if not isinstance(row, dict):
                    continue
                team = row.get("team", {})
                team_id_val = team.get("id")
                team_name = team.get("name")
                if team_id_val in {team_id, opp_id}:
                    rows.append(
                        f"{team_name}: pos {row.get('position')}, pts {row.get('points')}"
                    )
            if rows:
                chunks.append(f"{group.group}: " + ", ".join(rows))
        return "; ".join(chunks) if chunks else "standings unavailable."

    return [get_team_form, get_opponent_form, get_group_standings]


def player_tools(state) -> list[BaseTool]:
    """Tools for finding the focus team's leading scorer and fetching their bio."""
    team_id = state.get("team_id")
    team_name = state.get("team_name") or "the focus team"

    @tool
    async def get_top_scorers() -> str:
        """Get World Cup top scorers (deep list) to find the focus team's leading scorer."""
        async with FootballDataClient() as c:
            r = await c.top_scorers(100)
        if not r.ok or not r.data:
            return "scorers unavailable."
        team_scorers = [
            s
            for s in r.data
            if (team_id and s.team.id == team_id)
            or (s.team.name and team_name.lower() in s.team.name.lower())
        ]
        if not team_scorers:
            return f"{team_name} has no scorer in the World Cup yet."
        lines = [
            f"{s.player.name}: {s.goals} goals ({s.team.name})"
            for s in team_scorers[:5]
        ]
        return "\n".join(lines)

    @tool
    async def get_player_profile(player_name: str) -> str:
        """Look up a player's position, club, and nationality by name."""
        async with SportsDbClient() as c:
            r = await c.player_profile(player_name)
        if not r.ok or not r.data:
            return f"no profile for '{player_name}'."
        p = r.data
        return (
            f"{p.name}: {p.position or 'unknown position'}, "
            f"{p.club or 'unknown club'}, {p.nationality or 'unknown nationality'}"
        )

    return [get_top_scorers, get_player_profile]


def news_tools(state) -> list[BaseTool]:
    """Tools for RSS headlines and optional Tavily news search."""
    team_name = state.get("team_name") or "the team"
    opponent_name = state.get("opponent_name")

    @tool
    async def fetch_rss_headlines() -> str:
        """Fetch recent football RSS headlines mentioning the focus team."""
        async with NewsClient() as c:
            r = await c.fetch_rss(team_name, 6)
        if not r.ok or not r.data:
            return "rss headlines unavailable."
        return "\n".join(f"- {i.title} ({i.source})" for i in r.data)

    @tool
    async def search_team_news() -> str:
        """Search the web for fresh team news, injuries, and storylines."""
        async with NewsClient() as c:
            r = await c.search_tavily(team_name, opponent_name)
        if not r.ok:
            return r.error or "news search unavailable."
        if not r.data:
            return "no news results."
        return "\n".join(f"- {i.title}: {i.summary}" for i in r.data)

    return [fetch_rss_headlines, search_team_news]