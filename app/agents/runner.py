"""Step 7 — Hand-rolled ReAct loop (Reason + Act).

The model reasons, calls tools, reads results, and repeats until it can answer.
We hand-roll the loop (instead of a deprecated prebuilt helper) so every step is
visible. ``ainvoke_with_backoff`` self-heals Groq 429 rate-limit bursts.
"""

import asyncio
import re

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.config import agent_model
from app.state import Finding

# Module-level log used by ``--verbose`` in main.py
_TOOL_LOG: list[str] = []


def get_tool_log() -> list[str]:
    """Return tool-call lines collected during the last graph run."""
    return _TOOL_LOG


def clear_tool_log() -> None:
    """Reset the verbose tool log before a new run."""
    _TOOL_LOG.clear()


def _text(content) -> str:
    """Normalize LLM response content to a plain string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _is_rate_limit(exc: Exception) -> bool:
    """True when Groq rejected the call for TPM/TPD limits."""
    msg = str(exc).lower()
    return "429" in msg or "rate_limit" in msg or "tokens per minute" in msg


def _suggested_wait(exc: Exception) -> float:
    """Parse Groq's suggested wait time from a 429 error message."""
    match = re.search(r"wait (\d+)", str(exc), re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 5.0


async def ainvoke_with_backoff(model, messages, retries=2):
    """Call the model, backing off on rate-limit errors instead of failing the run."""
    for attempt in range(retries + 1):
        try:
            return await model.ainvoke(messages)
        except Exception as exc:
            if attempt == retries or not _is_rate_limit(exc):
                raise
            await asyncio.sleep(min(_suggested_wait(exc), 15.0))


async def run_tool_agent(model, tools, system, task, *, max_iters=4, tool_log=None, agent_name=None):
    """ReAct loop: bind_tools → model decides → we execute → ToolMessage → repeat.

    ``max_iters`` caps confused models. Tool output is truncated to 1500 chars to
    control token use on Groq's free tier.
    """
    by_name = {t.name: t for t in tools}
    bound = model.bind_tools(tools)
    messages = [SystemMessage(content=system), HumanMessage(content=task)]

    for _ in range(max_iters):
        ai = await ainvoke_with_backoff(bound, messages)
        messages.append(ai)
        if not ai.tool_calls:
            return _text(ai.content)

        names = [call["name"] for call in ai.tool_calls]
        if tool_log is not None and names:
            prefix = f"· {agent_name} " if agent_name else "· "
            tool_log.append(f"{prefix}called tools: {', '.join(names)}")

        for call in ai.tool_calls:
            tool = by_name.get(call["name"])
            if tool is None:
                result = f"unknown tool: {call['name']}"
            else:
                result = await tool.ainvoke(call["args"])
            messages.append(
                ToolMessage(
                    content=str(result)[:1500],
                    tool_call_id=call["id"],
                )
            )

    return "Agent stopped: max iterations reached."


async def run_agent_finding(agent_name, title, tools, system, task, *, tool_log=None):
    """Run the ReAct loop and package the answer into a ``Finding`` for the graph."""
    log = tool_log if tool_log is not None else _TOOL_LOG
    try:
        text = await run_tool_agent(
            agent_model(), tools, system, task, tool_log=log, agent_name=agent_name
        )
        ok = bool(text.strip()) and "unavailable" not in text.lower()
        return {
            "findings": [
                Finding(agent=agent_name, title=title, content=text, ok=ok)
            ]
        }
    except Exception as exc:
        transient = _is_rate_limit(exc)
        return {
            "findings": [
                Finding(
                    agent=agent_name,
                    title=title,
                    content=str(exc),
                    ok=False,
                    transient=transient,
                )
            ]
        }