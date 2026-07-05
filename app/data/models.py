"""Step 2 — Pydantic data models for external API payloads.

The football API speaks camelCase (``utcDate``); aliases map those to clean Python
names. Every match field is optional so thin payloads (e.g. scheduled fixtures
with no score yet) never fail validation.
"""

from pydantic import BaseModel, ConfigDict, Field


class _Camel(BaseModel):
    """Shared base: accept camelCase JSON keys and ignore unknown fields."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",  # drop fields we didn't define rather than raising
    )


class TeamRef(_Camel):
    """Minimal team reference returned by football-data.org."""

    id: int | None = None
    name: str | None = None


class PlayerRef(_Camel):
    """Player reference inside competition scorer payloads."""

    id: int | None = None
    name: str | None = None


class Scorer(_Camel):
    """One row from the competition-wide top scorers list."""

    player: PlayerRef = Field(default_factory=PlayerRef)
    team: TeamRef = Field(default_factory=TeamRef)
    goals: int | None = None


class GroupStanding(_Camel):
    """One World Cup group's TOTAL standings table."""

    group: str | None = None
    table: list = Field(default_factory=list)


class NewsItem(_Camel):
    """Normalized headline from RSS or Tavily search."""

    source: str
    title: str
    link: str | None = None
    summary: str | None = None


class PlayerProfile(BaseModel):
    """Player bio from TheSportsDB (position, club, nationality)."""

    name: str
    position: str | None = None
    club: str | None = None
    nationality: str | None = None


class ScoreDetail(_Camel):
    home: int | None = None
    away: int | None = None


class Score(_Camel):
    full_time: ScoreDetail = Field(default_factory=ScoreDetail, alias="fullTime")


# Define a match model with every field optional so a thin payload never fails validation
class Match(_Camel):
    """One fixture from football-data.org."""

    utc_date: str | None = Field(default=None, alias="utcDate")
    status: str | None = None
    venue: str | None = None
    home_team: TeamRef = Field(default_factory=TeamRef, alias="homeTeam")
    away_team: TeamRef = Field(default_factory=TeamRef, alias="awayTeam")
    score: Score = Field(default_factory=Score)