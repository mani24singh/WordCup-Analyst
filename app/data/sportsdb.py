"""Step 4 — Player bio client (archivist).

The free football tier has top scorers but no per-player bios. TheSportsDB's public
demo key (123) returns position, club, and nationality for a player name search.
"""

import httpx

from app.data.models import PlayerProfile
from app.data.results import ApiResult, explain_error, is_transient


class SportsDbClient:
    """Player profile lookup via TheSportsDB free API."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url="https://www.thesportsdb.com/api/v1/json/123",
            timeout=15.0,
        )

    async def __aenter__(self) -> "SportsDbClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self._http.aclose()

    async def player_profile(self, name: str) -> ApiResult[PlayerProfile]:
        """Look up a player by name and return their bio fields."""
        try:
            resp = await self._http.get("/searchplayers.php", params={"p": name})
            resp.raise_for_status()
            players = resp.json().get("player") or []
            if not players:
                return ApiResult(error=f"no profile for '{name}'")
            raw = players[0]
            return ApiResult(
                data=PlayerProfile(
                    name=raw.get("strPlayer"),
                    position=raw.get("strPosition"),
                    club=raw.get("strTeam"),
                    nationality=raw.get("strNationality"),
                )
            )
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))