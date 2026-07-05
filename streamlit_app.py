"""Streamlit UI for WordCup-Analyst briefings."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.config import apply_settings
from app.main import run_briefing
from app.ui.docx_export import build_briefing_docx, build_setup_guide_docx

IMAGE_DIR = ROOT / "app" / "image"


def _hero_image() -> Path | None:
    for name in ("background.png", "image.png"):
        path = IMAGE_DIR / name
        if path.is_file():
            return path
    return None

APP_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg: #0d0d0d;
        --surface: #161616;
        --surface-2: #1f1f1f;
        --border: #2e2e2e;
        --border-accent: #7f1d1d;
        --text: #fafafa;
        --muted: #a1a1a1;
        --accent: #e11d48;
        --accent-dim: #be123c;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes softPulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(225, 29, 72, 0.35); }
        50%       { box-shadow: 0 0 0 8px rgba(225, 29, 72, 0); }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    @keyframes footballRoam {
        0%   { left: 5%;  top: 18%; }
        18%  { left: 72%; top: 12%; }
        36%  { left: 90%; top: 42%; }
        54%  { left: 62%; top: 78%; }
        72%  { left: 18%; top: 72%; }
        88%  { left: 8%;  top: 38%; }
        100% { left: 5%;  top: 18%; }
    }

    @keyframes footballBounce {
        0%, 100% { transform: translateY(0) rotate(0deg) scale(1); }
        35%      { transform: translateY(-36px) rotate(140deg) scale(1.05); }
        70%      { transform: translateY(-8px) rotate(280deg) scale(0.98); }
    }

    .wc-football-roam {
        position: fixed;
        z-index: 50;
        pointer-events: none;
        user-select: none;
        font-size: 2rem;
        line-height: 1;
        opacity: 0.82;
        filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.55));
        animation: footballRoam 26s ease-in-out infinite;
    }

    .wc-football-ball {
        display: inline-block;
        animation: footballBounce 0.62s ease-in-out infinite;
    }

    .stApp {
        background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(127, 29, 29, 0.35), transparent),
                    var(--bg);
        font-family: 'Inter', sans-serif;
        color: var(--text);
    }

    .stApp header[data-testid="stHeader"] {
        background: rgba(13, 13, 13, 0.9) !important;
        border-bottom: 1px solid var(--border);
    }

    div[data-testid="stSidebar"] {
        background: #111111 !important;
        border-right: 1px solid var(--border);
    }

    section.main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
        max-width: 1200px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-left: 3px solid var(--accent) !important;
        border-radius: 12px !important;
        animation: fadeInUp 0.45s ease-out;
    }

    .page-header {
        animation: fadeInUp 0.4s ease-out;
        margin-bottom: 1.5rem;
        text-align: center;
    }

    .eyebrow {
        display: block;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 0.5rem;
    }

    .page-title {
        font-size: 2.85rem;
        font-weight: 700;
        color: var(--text);
        margin: 0;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }

    .page-sub {
        color: var(--muted);
        font-size: 0.95rem;
        margin: 0.55rem auto 0 auto;
        max-width: 520px;
    }

    .sidebar-byok {
        text-align: center;
        padding-bottom: 1rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--border);
    }

    .sidebar-byok-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--accent);
        margin: 0;
        letter-spacing: 0.04em;
    }

    .sidebar-byok-sub {
        font-size: 0.78rem;
        color: var(--muted);
        margin: 0.3rem 0 0 0;
    }

    .status-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.45rem;
        margin-top: 1rem;
    }

    .status-item {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.5rem 0.65rem;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--muted);
        animation: fadeIn 0.5s ease-out;
    }

    .status-item.ok {
        border-color: var(--border-accent);
        color: #fecdd3;
        background: rgba(127, 29, 29, 0.2);
    }

    .status-item.warn {
        border-color: #713f12;
        color: #fde68a;
        background: rgba(113, 63, 18, 0.2);
    }

    .section-label {
        color: #737373;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0 0 0.55rem 0;
    }

    .visual-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
        animation: fadeInUp 0.55s ease-out 0.1s both;
        height: 100%;
    }

    .visual-card img {
        display: block;
        width: 100%;
        height: auto;
    }

    .visual-caption {
        padding: 0.8rem 1rem;
        border-top: 1px solid var(--border);
        background: var(--surface-2);
    }

    .visual-caption strong {
        display: block;
        color: var(--text);
        font-size: 0.84rem;
    }

    .visual-caption span {
        color: var(--muted);
        font-size: 0.76rem;
    }

    .hint-line {
        color: var(--muted);
        font-size: 0.84rem;
        margin-bottom: 0.75rem;
        padding: 0.7rem 0.95rem;
        background: var(--surface);
        border-radius: 10px;
        border: 1px solid var(--border);
        animation: fadeIn 0.4s ease-out;
    }

    .briefing-zone {
        animation: fadeInUp 0.6s ease-out;
        margin-top: 0.5rem;
    }

    .fixture-badge {
        display: inline-block;
        background: rgba(127, 29, 29, 0.25);
        border: 1px solid var(--border-accent);
        color: #fecdd3;
        font-weight: 600;
        font-size: 0.82rem;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.85rem;
    }

    .correction-note {
        background: rgba(127, 29, 29, 0.2);
        border: 1px solid var(--border-accent);
        color: #fecdd3;
        border-radius: 10px;
        padding: 0.7rem 0.95rem;
        font-size: 0.86rem;
        margin-bottom: 0.85rem;
    }

    .briefing-panel {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem 1.75rem;
        color: #d4d4d4;
        line-height: 1.7;
        margin-bottom: 1rem;
    }

    .briefing-panel h1, .briefing-panel h2, .briefing-panel h3 {
        color: var(--text);
    }

    .sidebar-label {
        color: #d4d4d4;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }

    .stButton > button[kind="primary"] {
        background: var(--accent) !important;
        color: #fff !important;
        border: none !important;
        font-weight: 600;
        border-radius: 10px;
        height: 2.8rem;
        animation: softPulse 2.5s ease-in-out infinite;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--accent-dim) !important;
        animation: none;
    }

    div[data-testid="stSidebar"] .stDownloadButton > button,
    .stDownloadButton > button {
        background: var(--surface);
        color: #fca5a5;
        border: 1px solid var(--border-accent);
        font-size: 0.8rem;
        border-radius: 8px;
    }

    .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
        background-color: #0d0d0d !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }

    .footer-note {
        color: #525252;
        font-size: 0.75rem;
        text-align: center;
        margin-top: 1.5rem;
    }

    @media (max-width: 768px) {
        .status-grid { grid-template-columns: 1fr; }
        .wc-football-roam { font-size: 1.5rem; opacity: 0.65; }
    }
</style>
"""


def _inject_bouncing_football() -> None:
    """Decorative football — pointer-events none, does not block clicks."""
    st.markdown(
        '<div class="wc-football-roam" aria-hidden="true">'
        '<span class="wc-football-ball">⚽</span></div>',
        unsafe_allow_html=True,
    )

EXAMPLE_QUERIES = [
    "Give me a briefing on Brazil's next match",
    "Brief me on France's next match",
    "Give me a briefing on Argentina's next match",
    "Who should I watch in Spain's next match?",
]

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

KEY_EXAMPLES = {
    "groq_key": "gsk_demo_a8f3k2m9x1p4q7r0",
    "football_key": "abc12def34ghi56jkl78mno90",
    "tavily_key": "tvly-demo-9xK2mP7qR4sT1vW8",
}


@lru_cache(maxsize=1)
def _setup_guide_docx() -> bytes:
    return build_setup_guide_docx()


def _init_session() -> None:
    """Initialize session — never pre-fill API keys from .env in the UI."""
    st.session_state.setdefault("query", EXAMPLE_QUERIES[0])
    st.session_state.setdefault("result", None)

    if not st.session_state.get("_ui_keys_cleared"):
        st.session_state.groq_key = ""
        st.session_state.football_key = ""
        st.session_state.tavily_key = ""
        st.session_state._ui_keys_cleared = True


def _session_get(key: str, default: str = "") -> str:
    return str(st.session_state.get(key, default)).strip()


def _apply_user_keys() -> None:
    apply_settings(
        groq_api_key=_session_get("groq_key"),
        football_token=_session_get("football_key"),
        tavily_api_key=_session_get("tavily_key"),
    )


def _validate_keys() -> list[str]:
    missing = []
    if not _session_get("groq_key"):
        missing.append("Groq")
    if not _session_get("football_key"):
        missing.append("Football Data")
    return missing


def _prompt_missing_keys(missing: list[str]) -> None:
    st.info(
        "🔑 Add your "
        + " and ".join(missing)
        + " API keys in the sidebar before generating a briefing. "
        "Download **API setup guide (.docx)** for step-by-step instructions."
    )


def _friendly_briefing_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if any(token in msg for token in ("401", "403", "api key", "auth", "token", "unauthorized", "invalid")):
        return (
            "Your API keys may be missing or incorrect. "
            "Create and add valid keys in the sidebar, using the setup guide if needed."
        )
    return "Something went wrong. Check your API keys and try again."


def _status_html() -> str:
    groq_ok = bool(_session_get("groq_key"))
    football_ok = bool(_session_get("football_key"))
    tavily_ok = bool(_session_get("tavily_key"))
    icons = {"Groq": "🤖", "Football Data": "⚽", "Tavily": "📰"}
    items = [
        ("Groq", groq_ok, True),
        ("Football Data", football_ok, True),
        ("Tavily", tavily_ok, False),
    ]
    cells = []
    for name, ok, required in items:
        icon = icons.get(name, "")
        if ok:
            cls, label = "ok", "Ready ✓"
        elif required:
            cls, label = "warn", "Missing"
        else:
            cls, label = "", "Optional"
        cells.append(f'<div class="status-item {cls}">{icon} {name} · {label}</div>')
    return '<div class="status-grid">' + "".join(cells) + "</div>"


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-byok">
                <p class="sidebar-byok-title">BYOK</p>
                <p class="sidebar-byok-sub">Bring your own keys</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<p class="sidebar-label">🔐 Credentials</p>', unsafe_allow_html=True)

        st.text_input(
            "Groq API Key",
            key="groq_key",
            type="password",
            placeholder=KEY_EXAMPLES["groq_key"],
        )
        st.text_input(
            "Football Data Token",
            key="football_key",
            type="password",
            placeholder=KEY_EXAMPLES["football_key"],
        )
        st.text_input(
            "Tavily Key (optional)",
            key="tavily_key",
            type="password",
            placeholder=KEY_EXAMPLES["tavily_key"],
        )

        st.download_button(
            label="🔑 API setup guide (.docx)",
            data=_setup_guide_docx(),
            file_name="api_keys_setup.docx",
            mime=DOCX_MIME,
            use_container_width=True,
            key="setup_guide_download",
        )
        st.caption("Keys stay in this session only.")
        st.divider()
        st.caption("🧠 Agents: Matchup · Player · News")


def _render_visual_panel() -> None:
    st.markdown('<div class="visual-card">', unsafe_allow_html=True)
    hero = _hero_image()
    if hero:
        st.image(str(hero), use_container_width=True)
    st.markdown(
        """
        <div class="visual-caption">
            <strong>🏆 2026 FIFA World Cup</strong>
            <span>Live fixtures · form · players · news</span>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_controls() -> bool:
    """Left column: status, query form, generate button."""
    missing = _validate_keys()
    if missing:
        st.markdown(
            f'<p class="hint-line">🔑 Add {" and ".join(missing)} keys in the sidebar to begin.</p>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="section-label">💬 Ask a question</p>', unsafe_allow_html=True)

    with st.container(border=True):
        example = st.selectbox(
            "Examples",
            options=["Choose an example…", *EXAMPLE_QUERIES],
            label_visibility="collapsed",
        )
        if example != "Choose an example…":
            st.session_state.query = example

        st.text_area(
            "Question",
            key="query",
            height=100,
            placeholder="Give me a briefing on Brazil's next match",
            label_visibility="collapsed",
        )
        st.caption("✨ Team names auto-correct — Brasil, USA, Holland, Korea…")
        return st.button("⚽ Generate briefing", type="primary", use_container_width=True)


def _render_briefing_full_width(result: dict) -> None:
    """Full-width briefing section below the top two columns."""
    st.markdown('<div class="briefing-zone">', unsafe_allow_html=True)
    st.markdown('<p class="section-label">📋 Match briefing</p>', unsafe_allow_html=True)

    if result.get("team_name_corrected") and result.get("team_name_input"):
        st.markdown(
            f'<div class="correction-note">✨ Resolved '
            f'<strong>{result["team_name_input"]}</strong> → '
            f'<strong>{result["team_name"]}</strong></div>',
            unsafe_allow_html=True,
        )

    if result.get("next_match"):
        st.markdown(
            f'<div class="fixture-badge">📅 {result["next_match"]}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="briefing-panel">', unsafe_allow_html=True)
    st.markdown(result.get("briefing", ""))
    st.markdown("</div>", unsafe_allow_html=True)

    team_slug = (result.get("team_name") or "worldcup").lower().replace(" ", "_")
    filename = f"briefing_{team_slug}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"
    st.download_button(
        label="📥 Download briefing (.docx)",
        data=build_briefing_docx(result),
        file_name=filename,
        mime=DOCX_MIME,
        use_container_width=True,
        key="briefing_download",
    )
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="WorldCup Analyst",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    _inject_bouncing_football()
    _init_session()
    _render_sidebar()

    st.markdown(
        """
        <div class="page-header">
            <span class="eyebrow">FIFA World Cup 2026</span>
            <p class="page-title">⚽ WorldCup Analyst</p>
            <p class="page-sub">Parallel AI agents build match-day briefings from live football data.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_controls, col_image = st.columns([1.2, 1], gap="large")

    with col_controls:
        st.markdown(_status_html(), unsafe_allow_html=True)
        generate = _render_controls()

    with col_image:
        _render_visual_panel()

    if generate:
        missing = _validate_keys()
        if missing:
            _prompt_missing_keys(missing)
        elif not _session_get("query"):
            st.info("💬 Enter a briefing question, then click **Generate briefing**.")
        else:
            _apply_user_keys()
            with st.spinner("🔄 Running agents in parallel…"):
                try:
                    st.session_state.result = asyncio.run(
                        run_briefing(_session_get("query"))
                    )
                except Exception as exc:
                    st.session_state.result = None
                    st.warning(_friendly_briefing_error(exc))

    result = st.session_state.result
    if result:
        st.divider()
        if result.get("team_resolve_error"):
            st.warning(
                f"🏳️ {result['team_resolve_error']} "
                "Try a valid World Cup team (e.g. Brazil, France, USA)."
            )
        else:
            _render_briefing_full_width(result)

    st.markdown(
        '<p class="footer-note">⚽ football-data.org · Groq · Tavily</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()