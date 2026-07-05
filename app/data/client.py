"""Step 3 — Async football-data.org client.

The only place that talks to football-data.org. Async lets three agents call it at
the same time while waiting on the network. A 90-second in-memory cache protects
the free tier's 10 requests/minute limit.
"""

import time
from datetime import date, timedelta

import httpx

from app.config import SETTINGS
from app.data.models import GroupStanding, Match, Scorer, TeamRef
from app.data.results import ApiResult, explain_error, is_transient
from app.data.teams import ResolvedTeam, match_team, suggest_teams

# In-memory cache: keyed by URL, reused for 90 seconds to avoid 429 Too Many Requests
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 90.0


class FootballDataClient:
    """Official World Cup statistics from football-data.org v4."""

    def __init__(self) -> None:
        self._token = SETTINGS.football_token
        headers = {"X-Auth-Token": self._token} if self._token else {}
        self._http = httpx.AsyncClient(
            base_url="https://api.football-data.org/v4",
            headers=headers,
            timeout=15.0,
        )

    async def __aenter__(self) -> "FootballDataClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self._http.aclose()

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """Low-level GET with caching. ``await`` yields control while the network responds."""
        key = path + "?" + str(sorted((params or {}).items()))
        # inside _get(), before the network call:
        cached = _CACHE.get(key)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]
        response = await self._http.get(path, params=params)
        response.raise_for_status()
        data = response.json()
        _CACHE[key] = (time.monotonic(), data)
        return data

    async def standings(self) -> ApiResult[list[GroupStanding]]:
        """Current World Cup group tables (TOTAL type only)."""
        try:
            payload = await self._get(f"/competitions/WC/standings")
            groups = [
                GroupStanding.model_validate(s)
                for s in payload.get("standings", [])
                if s.get("type") == "TOTAL"
            ]
            return ApiResult(data=groups)
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))

    _DONE_STATUSES = frozenset({"FINISHED", "CANCELLED", "POSTPONED", "AWARDED"})

    async def next_match(self, team_id: int) -> ApiResult[Match]:
        """Soonest World Cup fixture for a team that has not finished yet."""
        try:
            today = date.today()
            payload = await self._get(
                f"/teams/{team_id}/matches",
                params={
                    "competitions": "WC",
                    # Look a few days back so a fixture dated "yesterday" in UTC/local
                    # is still returned while status is TIMED/SCHEDULED/IN_PLAY.
                    "dateFrom": (today - timedelta(days=3)).isoformat(),
                    "dateTo": (today + timedelta(days=90)).isoformat(),
                },
            )
            upcoming = [
                m
                for m in (Match.model_validate(x) for x in payload.get("matches", []))
                if m.status not in self._DONE_STATUSES
            ]
            upcoming.sort(key=lambda m: m.utc_date or "")
            return ApiResult(data=upcoming[0]) if upcoming else ApiResult(error="no fixture")
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))

    async def list_wc_teams(self) -> ApiResult[list[TeamRef]]:
        """All teams registered for the World Cup competition."""
        try:
            payload = await self._get("/competitions/WC/teams")
            teams = [TeamRef.model_validate(raw) for raw in payload.get("teams", [])]
            return ApiResult(data=teams)
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))

    async def resolve_team_id(self, name: str) -> ApiResult[TeamRef]:
        """Look up a World Cup team by partial name match."""
        resolved = await self.resolve_team(name)
        if resolved.ok and resolved.data:
            return ApiResult(data=resolved.data.ref)
        return ApiResult(error=resolved.error or f"no team '{name}'")

    async def resolve_team(self, name: str) -> ApiResult[ResolvedTeam]:
        """Resolve a user-supplied team name with alias and fuzzy matching."""
        try:
            teams_result = await self.list_wc_teams()
            if not teams_result.ok or not teams_result.data:
                return ApiResult(error=teams_result.error or "teams unavailable")

            matched = match_team(name, teams_result.data)
            if matched:
                return ApiResult(data=matched)

            hints = suggest_teams(name, teams_result.data)
            hint = f" Did you mean: {', '.join(hints)}?" if hints else ""
            return ApiResult(error=f"no team '{name}'.{hint}")
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))

    async def team_form(self, team_id: int, limit: int = 5) -> ApiResult[list[Match]]:
        """Last N finished matches for W/D/L form analysis."""
        try:
            payload = await self._get(
                f"/teams/{team_id}/matches",
                params={"competitions": "WC", "limit": limit},
            )
            matches = [Match.model_validate(x) for x in payload.get("matches", [])]
            finished = [m for m in matches if m.status == "FINISHED"]
            return ApiResult(data=finished[:limit])
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))

    async def top_scorers(self, limit: int = 100) -> ApiResult[list[Scorer]]:
        """Competition scorers — deep slice (100) so low-scoring teams still appear."""
        try:
            payload = await self._get(f"/competitions/WC/scorers", params={"limit": limit})
            scorers = [Scorer.model_validate(s) for s in payload.get("scorers", [])]
            return ApiResult(data=scorers)
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))