"""Step 5 — Shared state and reducers.

State is the clipboard passed between LangGraph nodes. List fields that receive
parallel writes use ``operator.add`` as a reducer so findings are merged, not
overwritten. ``total=False`` means not every key must be present on every node.
"""

import operator
from dataclasses import dataclass
from typing import Annotated, TypedDict


@dataclass
class Finding:
    """One agent's written section, packaged for the synthesizer."""

    agent: str  # which agent produced this
    title: str  # section heading
    content: str  # the written text
    ok: bool  # did it have real data?
    transient: bool = False  # if it failed, is a retry worth it?


class AnalystState(TypedDict, total=False):
    """Shared graph state — supervisor fills routing keys, agents append findings."""

    query: str
    team_name: str | None
    team_name_input: str | None
    team_name_corrected: bool
    team_resolve_error: str | None
    team_id: int | None
    opponent_name: str | None
    opponent_id: int | None
    next_match: str | None
    jobs: list[str]
    findings: Annotated[list[Finding], operator.add]  # merged, not overwritten
    missing: Annotated[list[str], operator.add]
    retries: int
    briefing: str | None