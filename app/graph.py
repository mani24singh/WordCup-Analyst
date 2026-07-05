"""Step 11 — LangGraph wiring with parallel fan-out via Send.

``Send`` launches multiple node-runs in one superstep. All agent edges into the
synthesizer create automatic fan-in — it waits until every dispatched agent
finishes. The retry edge only fires for transient failures (timeout / 429).
"""

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from app.agents.matchup import matchup_node
from app.agents.news import news_node
from app.agents.player import player_node
from app.agents.supervisor import ALL_JOBS, supervisor_node
from app.agents.synthesizer import latest_findings, synthesizer_node
from app.state import AnalystState

_WORKERS = {
    "matchup_agent": matchup_node,
    "player_agent": player_node,
    "news_agent": news_node,
}


def _fan_out(state):
    """Return one Send per chosen agent — LangGraph runs them all concurrently."""
    return [Send(job, state) for job in state.get("jobs", []) if job in _WORKERS]


def _after_synthesis(state):
    """Retry once on transient agent failures; stop on permanent errors."""
    findings = latest_findings(state.get("findings") or [])
    transient_failure = any(not f.ok and f.transient for f in findings)
    if transient_failure and state.get("retries", 0) < 1:
        return Command(
            goto="supervisor",
            update={"retries": state.get("retries", 0) + 1},
        )
    return END


def build_graph():
    """Compile the full supervisor → parallel agents → synthesizer workflow."""
    graph = StateGraph(AnalystState)
    graph.add_node("supervisor", supervisor_node)
    for name, node in _WORKERS.items():
        graph.add_node(name, node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", _fan_out, list(ALL_JOBS))  # parallel launch
    for name in _WORKERS:
        graph.add_edge(name, "synthesizer")  # all feed synth
    graph.add_conditional_edges("synthesizer", _after_synthesis, ["supervisor", END])

    return graph.compile()