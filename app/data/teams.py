"""World Cup team name normalization and fuzzy matching."""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

from app.data.models import TeamRef

# Common nicknames, typos, and alternate country names → official API name.
ALIASES: dict[str, str] = {
    "america": "United States",
    "aus": "Australia",
    "bosnia": "Bosnia-Herzegovina",
    "brasil": "Brazil",
    "britain": "England",
    "cape verde": "Cape Verde Islands",
    "congo": "Congo DR",
    "cote divoire": "Ivory Coast",
    "curacao": "Curaçao",
    "czech": "Czechia",
    "czech republic": "Czechia",
    "deutschland": "Germany",
    "dr congo": "Congo DR",
    "drc": "Congo DR",
    "england": "England",
    "espana": "Spain",
    "españa": "Spain",
    "holland": "Netherlands",
    "iran": "Iran",
    "ivory coast": "Ivory Coast",
    "korea": "South Korea",
    "mexico": "Mexico",
    "méxico": "Mexico",
    "netherlands": "Netherlands",
    "persia": "Iran",
    "republic of korea": "South Korea",
    "saudi": "Saudi Arabia",
    "south korea": "South Korea",
    "spain": "Spain",
    "the netherlands": "Netherlands",
    "uk": "England",
    "us": "United States",
    "usa": "United States",
    "u s": "United States",
    "u s a": "United States",
}


@dataclass(frozen=True)
class ResolvedTeam:
    """Result of matching a user-supplied name to an official World Cup team."""

    ref: TeamRef
    query_name: str
    matched_name: str

    @property
    def corrected(self) -> bool:
        return _normalize(self.query_name) != _normalize(self.matched_name)


def _normalize(text: str) -> str:
    """Lowercase, strip accents, and remove punctuation for comparison."""
    text = unicodedata.normalize("NFKD", text.strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _by_official_name(teams: list[TeamRef]) -> dict[str, TeamRef]:
    return {_normalize(team.name or ""): team for team in teams if team.name}


def _best_fuzzy(query: str, choices: list[str], *, cutoff: float = 0.72) -> str | None:
    matches = difflib.get_close_matches(query, choices, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def match_team(query: str, teams: list[TeamRef]) -> ResolvedTeam | None:
    """Map a free-text team name to the closest official World Cup team."""
    raw = query.strip()
    if not raw:
        return None

    official = _by_official_name(teams)
    normalized = _normalize(raw)

    # 1. Exact official name
    if normalized in official:
        team = official[normalized]
        return ResolvedTeam(ref=team, query_name=raw, matched_name=team.name or raw)

    # 2. Known alias
    alias_target = ALIASES.get(normalized)
    if alias_target:
        alias_key = _normalize(alias_target)
        if alias_key in official:
            team = official[alias_key]
            return ResolvedTeam(ref=team, query_name=raw, matched_name=team.name or alias_target)

    # 3. Substring on official names (prefer longest name to avoid partial collisions)
    substring_hits = [
        team
        for key, team in official.items()
        if normalized in key or key in normalized
    ]
    if substring_hits:
        best = max(substring_hits, key=lambda t: len(t.name or ""))
        return ResolvedTeam(ref=best, query_name=raw, matched_name=best.name or raw)

    # 4. Fuzzy on official names
    fuzzy_official = _best_fuzzy(normalized, list(official.keys()))
    if fuzzy_official:
        team = official[fuzzy_official]
        return ResolvedTeam(ref=team, query_name=raw, matched_name=team.name or raw)

    # 5. Fuzzy on alias keys, then map to official
    fuzzy_alias = _best_fuzzy(normalized, list(ALIASES.keys()), cutoff=0.78)
    if fuzzy_alias:
        alias_key = _normalize(ALIASES[fuzzy_alias])
        if alias_key in official:
            team = official[alias_key]
            return ResolvedTeam(ref=team, query_name=raw, matched_name=team.name or raw)

    return None


def suggest_teams(query: str, teams: list[TeamRef], *, limit: int = 4) -> list[str]:
    """Return nearby official team names when no confident match exists."""
    normalized = _normalize(query)
    if not normalized:
        return []

    names = [team.name for team in teams if team.name]
    ranked = difflib.get_close_matches(normalized, [_normalize(n) for n in names], n=limit, cutoff=0.45)
    lookup = {_normalize(name): name for name in names}
    return [lookup[key] for key in ranked if key in lookup]