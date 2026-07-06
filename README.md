<div align="center">

# WorldCup-Analyst

**Parallel multi-agent FIFA World Cup match-day briefings**

<br>

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.4-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-F59E0B?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-Llama-F55036?style=for-the-badge)
![Multi-Agent](https://img.shields.io/badge/Multi--Agent-Orchestration-8B5CF6?style=for-the-badge)
![Pydantic](https://img.shields.io/badge/Pydantic-2.x-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![httpx](https://img.shields.io/badge/httpx-Async-5A67D8?style=for-the-badge)
![feedparser](https://img.shields.io/badge/feedparser-RSS-00ADD8?style=for-the-badge)
![Tavily](https://img.shields.io/badge/Tavily-Search-0EA5E9?style=for-the-badge)

<br>

![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)
![API](https://img.shields.io/badge/API-Free%20Tier-success?style=flat-square)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://worldcup-analyst-2026.streamlit.app/)

<br>

*Ask one question. Three agents gather data in parallel. One synthesizer writes the briefing.*

**Live app:** [https://worldcup-analyst-2026.streamlit.app/](https://worldcup-analyst-2026.streamlit.app/)

</div>

---

Ask a single question — *"Give me a briefing on Brazil's next match"* — and receive a structured preview covering form, a key player, and the latest storylines. Three specialist agents work in parallel; a synthesizer merges their output into one cohesive briefing.

---

## Table of Contents

- [Live Demo](#live-demo)
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Verification & Testing](#verification--testing)
- [Project Structure](#project-structure)
- [Rate Limits](#rate-limits)
- [Troubleshooting](#troubleshooting)

---

## Live Demo

Try the app in your browser (BYOK — bring your own API keys):

**[https://worldcup-analyst-2026.streamlit.app/](https://worldcup-analyst-2026.streamlit.app/)**

| Main dashboard | Sample briefing output |
|----------------|------------------------|
| ![Main dashboard](app/image/Output-1.png) | ![Sample briefing](app/image/Output-2.png) |

*Left: query panel, API credentials, and generate flow. Right: Brazil vs Norway briefing with form, key player, and news sections.*

### Run locally

```bash
streamlit run streamlit_app.py
```

---

## Overview

WorldCup-Analyst is a command-line research assistant for the FIFA World Cup. A **supervisor** routes the user's question and resolves the next fixture once. Three **worker agents** then gather complementary data in parallel. A **synthesizer** writes the final reader-facing briefing.

The design follows the multi-agent orchestration pattern used in production research tools: delegate sub-questions to specialists, merge answers, keep the user interface simple.

---

## Features

- **Parallel agent execution** — matchup, player, and news agents run concurrently via LangGraph `Send`
- **Two-model LLM strategy** — 8B for tool loops (high free-tier budget), 70B for final synthesis
- **Hand-rolled ReAct agents** — transparent reason → act → observe loops with rate-limit backoff
- **Resilient data layer** — every API call returns `ApiResult`; one failure degrades a section, not the whole run
- **HTTP caching** — 90-second in-memory cache protects football-data.org's 10 req/min limit
- **Graceful synthesis fallback** — 70B → 8B → plain concatenation when Groq budgets are exhausted
- **Zero-cost operation** — runs on Groq, football-data.org, RSS, and TheSportsDB free tiers

---

## Tech Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) 1.2 | Parallel fan-out / fan-in workflow |
| LLM | [LangChain + Groq](https://console.groq.com/) | `llama-3.1-8b-instant` (agents), `llama-3.3-70b-versatile` (synthesis) |
| HTTP | [httpx](https://www.python-httpx.org/) | Async API clients |
| Validation | [Pydantic](https://docs.pydantic.dev/) 2.x | Typed models for external JSON |
| News | [feedparser](https://feedparser.readthedocs.io/) + [Tavily](https://tavily.com/) | RSS headlines + optional web search |
| Config | [python-dotenv](https://github.com/theskumar/python-dotenv) | Environment variable loading |
| Runtime | Python 3.12+ | Async-first execution |

### Data Sources

| Source | Data |
|--------|------|
| [football-data.org](https://www.football-data.org/) | Standings, fixtures, form, top scorers |
| BBC / Guardian RSS | Football headlines (no API key) |
| [TheSportsDB](https://www.thesportsdb.com/) | Player position, club, nationality |
| [Tavily](https://tavily.com/) *(optional)* | Targeted team news search |

---

## Architecture

```
User Query
    │
    ▼
┌─────────────┐
│ Supervisor  │  Route query · resolve team · fetch next fixture
└──────┬──────┘
       │  parallel fan-out (LangGraph Send)
   ┌───┼───┐
   ▼   ▼   ▼
┌─────┐ ┌─────┐ ┌─────┐
│Match│ │Player│ │News │   ReAct agents with per-run tool factories
│ up  │ │Scout │ │Feed │
└──┬──┘ └──┬──┘ └──┬──┘
   └───┬───┘
       ▼
┌─────────────┐
│ Synthesizer │  70B briefing writer (8B / concat fallback)
└──────┬──────┘
       ▼
   Briefing
```

| Component | Responsibility |
|-----------|----------------|
| Supervisor | Structured routing; resolves `team_id`, opponent, and `next_match` once |
| Matchup Agent | Form comparison and group standings |
| Player Agent | Leading scorer lookup and player bio |
| News Agent | RSS headlines and optional Tavily search |
| Synthesizer | Merges findings into a single markdown briefing |

---

## Prerequisites

- **Python** 3.12 or later
- **[uv](https://docs.astral.sh/uv/)** (recommended) or standard `venv` + `pip`
- **API keys** (all free, no credit card):

| Key | Required | Provider |
|-----|----------|----------|
| `GROQ_API_KEY` | Yes | [Groq Console](https://console.groq.com/keys) |
| `FOOTBALL_DATA_TOKEN` | Yes | [football-data.org](https://www.football-data.org/client/register) |
| `TAVILY_API_KEY` | No | [Tavily](https://app.tavily.com) |

---

## Installation

```bash
git clone <your-repo-url>
cd WorldCup-Analyst
```

**Using uv (recommended):**

```bash
uv venv
uv pip install -r requirements.txt
```

**Using venv + pip:**

```bash
python -m venv .venv
source .venv/bin/activate          # Git Bash / macOS / Linux
# .venv\Scripts\activate             # Windows PowerShell
pip install -r requirements.txt
```

**Verify dependencies:**

```bash
PYTHONPATH=. uv run python -c "import langgraph, langchain_groq, httpx; print('deps ok')"
```

Expected output: `deps ok`

---

## Configuration

Copy the example environment file and add your keys:

```bash
cp .env_example .env
```

```env
GROQ_API_KEY=your_groq_key
FOOTBALL_DATA_TOKEN=your_football_token
TAVILY_API_KEY=                   # optional — leave empty to use RSS only
```

> Never commit `.env` to version control.

---

## Usage

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

Open the sidebar, add your Groq and Football Data keys (download the setup guide from the app), ask a question, and click **Generate briefing**. Briefings download as `.docx`.

### Generate a briefing (CLI)

**Git Bash / macOS / Linux:**

```bash
PYTHONPATH=. uv run python app/main.py "Give me a briefing on Brazil's next match"
```

**Windows PowerShell:**

```powershell
$env:PYTHONPATH = "."
uv run python app/main.py "Give me a briefing on Brazil's next match"
```

**Verbose mode** (prints agent tool calls):

```bash
PYTHONPATH=. uv run python app/main.py "Brief me on France's next match" --verbose
```

### Example output

```
NEXT MATCH: Brazil vs Norway - 2026-07-05

### Brazil vs Norway - 2026-07-05
...
**Form & Matchup**: ...
**Key Player**: ...
**News & Storylines**: ...
```

---

## Verification & Testing

Three scripts validate each layer of the pipeline. They configure `PYTHONPATH` automatically — no prefix required.

| Script | Layer | Command |
|--------|-------|---------|
| `verify_client.py` | Football data client | `uv run python verify_client.py` |
| `verify_player.py` | Player scout agent | `uv run python verify_player.py` |
| `verify_run.py` | Full end-to-end workflow | `uv run python verify_run.py` |

### Layer checks

**Step 3 — Data client**

```bash
uv run python verify_client.py
# Expected: Brazil id: 764
```

**Step 8 — Player agent**

```bash
uv run python verify_player.py
# Expected: 2–3 sentences scouting a Brazilian player
```

**End-to-end — Full pipeline**

```bash
uv run python verify_run.py
uv run python verify_run.py "Give me a briefing on Brazil's next match"
uv run python verify_run.py "Brief me on France's next match" --verbose
```

Exits `0` on `VERIFICATION PASSED`, `1` on failure.

---

## Project Structure

```
WorldCup-Analyst/
├── app/
│   ├── config.py              # Settings and LLM model factories
│   ├── state.py                 # AnalystState + Finding reducer
│   ├── graph.py                 # LangGraph compilation
│   ├── main.py                  # CLI entry point
│   ├── data/
│   │   ├── client.py            # football-data.org async client
│   │   ├── news.py              # RSS + Tavily news client
│   │   ├── sportsdb.py          # TheSportsDB player bios
│   │   ├── models.py            # Pydantic data models
│   │   └── results.py           # ApiResult wrapper
│   └── agents/
│       ├── supervisor.py        # Router and fixture resolution
│       ├── matchup.py           # Form & standings agent
│       ├── player.py            # Key player scout
│       ├── news.py              # News & storylines agent
│       ├── synthesizer.py       # Briefing writer (fan-in)
│       ├── runner.py            # ReAct loop + backoff
│       └── tools.py             # Per-agent tool factories
├── verify_client.py             # Step 3 smoke test
├── verify_player.py             # Step 8 smoke test
├── verify_run.py                # End-to-end workflow test
├── requirements.txt
├── .env_example
└── README.md
```

---

## Rate Limits

This project is designed for free tiers. Be aware of these constraints:

| Service | Limit | Mitigation |
|---------|-------|------------|
| Groq 70B | ~100k tokens/day | Synthesizer falls back to 8B, then concatenation |
| Groq 8B | TPM cap per model | Agents use 8B; `ainvoke_with_backoff` retries on 429 |
| football-data.org | 10 requests/min | 90-second HTTP response cache |
| TheSportsDB (demo key) | ~30 req/min, truncated results | Per-player lookup only |

Upgrading to paid API tiers does not require architectural changes.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'app'` | Set `PYTHONPATH=.` or use `verify_*.py` scripts |
| `HTTP 403` from football-data.org | Verify `FOOTBALL_DATA_TOKEN` in `.env` |
| `SyntaxError` on `python -c` one-liner | Use multiline quotes or the dedicated verify scripts |
| Empty news section | Expected without Tavily; add `TAVILY_API_KEY` for richer coverage |
| `VERIFICATION FAILED` on first run | Check API keys; wait 60s if football-data rate-limited |

---
