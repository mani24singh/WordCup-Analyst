"""Step 10 — Synthesizer (fan-in) node.

Waits for all parallel agents, dedupes their findings, and writes one cohesive
briefing. Cascades 70b → 8b → plain concatenation so the user always gets
something readable even when the daily Groq budget is spent.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.runner import ainvoke_with_backoff
from app.config import agent_model, heavy_model
from app.state import Finding

_SYSTEM = (
    "You are a World Cup match-day editor. Write one cohesive briefing that opens "
    "with the fixture, then weaves Form & Matchup, Key Player, and News & Storylines "
    "into a readable preview. Use markdown section headings."
)


def latest_findings(findings: list[Finding]) -> list[Finding]:
    """Keep the latest finding per agent so a retry can't produce duplicate sections."""
    by_agent: dict[str, Finding] = {}
    for finding in findings:
        by_agent[finding.agent] = finding
    return list(by_agent.values())


def _fallback(query: str, findings: list[Finding]) -> str:
    """Last-resort briefing: concatenate agent sections without LLM polish."""
    parts = [f"Briefing for: {query}"]
    for f in latest_findings(findings):
        parts.append(f"**{f.title}**: {f.content}")
    return "\n\n".join(parts)


async def safe_analyse(model, system, user):
    """Try one model; return (text, success) without raising."""
    try:
        response = await ainvoke_with_backoff(
            model,
            [SystemMessage(content=system), HumanMessage(content=user)],
        )
        text = response.content if hasattr(response, "content") else str(response)
        return str(text), True
    except Exception:
        return "", False


async def synthesizer_node(state):
    """LangGraph fan-in node: merge findings into one reader-facing briefing."""
    findings = latest_findings(state.get("findings") or [])
    sections = "\n\n".join(f"**{f.title}**\n{f.content}" for f in findings)
    fixture = state.get("next_match") or "fixture unknown"
    team = state.get("team_name") or "the team"
    user = (
        f"Focus team: {team}\n"
        f"Next match: {fixture}\n\n"
        f"Agent findings:\n{sections}"
    )

    text, ok = await safe_analyse(heavy_model(), _SYSTEM, user)
    if not ok:  # 70b daily budget spent?
        text, ok = await safe_analyse(agent_model(), _SYSTEM, user)  # write on 8b
    return {"briefing": text if ok else _fallback(state.get("query", ""), findings)}