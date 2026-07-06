"""Streamlit-facing analytics layer — import only from streamlit_app.py."""

from __future__ import annotations

import uuid
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.analytics.client import AnalyticsClient
from app.analytics.gtag import parent_frame_gtag_html
from app.analytics.settings import ANALYTICS


class StreamlitAnalytics:
    """
    Detachable analytics facade for the Streamlit UI.

    Disable entirely: unset GA_MEASUREMENT_ID / GA_API_SECRET or set GA_ENABLED=false.
    Remove layer: delete imports and calls from streamlit_app.py.
    """

    def __init__(self) -> None:
        self._settings = ANALYTICS

    @property
    def active(self) -> bool:
        return self._settings.active

    def bind_session(self) -> None:
        """Ensure a stable anonymous client_id for this browser session."""
        if "analytics_client_id" not in st.session_state:
            st.session_state.analytics_client_id = str(uuid.uuid4())

    def _client(self) -> AnalyticsClient:
        return AnalyticsClient(
            self._settings,
            client_id=st.session_state.get("analytics_client_id", "unknown"),
        )

    def once_per_session(self, key: str, callback) -> None:
        flag = f"_ga_once_{key}"
        if st.session_state.get(flag):
            return
        callback()
        st.session_state[flag] = True

    def track(self, name: str, params: dict[str, Any] | None = None, **user_props: Any) -> None:
        user_properties = user_props or None
        self._client().track(name, params, user_properties=user_properties)

    def inject_client_tag(self) -> None:
        """
        Inject gtag.js into the Streamlit parent page (visible to Google Tag Assistant).

        Needs only GA_MEASUREMENT_ID. Disable with GA_CLIENT_INJECT=false.
        """
        if not self._settings.client_tag_active:
            return
        snippet = parent_frame_gtag_html(self._settings.measurement_id or "")
        if not snippet:
            return
        # st.html renders a component iframe; script escapes to parent.document
        if hasattr(st, "html"):
            st.html(snippet, height=0)
        else:
            components.html(snippet, height=0, width=0)

    def track_page_view(self) -> None:
        self.track(
            "page_view",
            {
                "page_title": "WorldCup Analyst",
                "page_location": "streamlit_app",
                "engagement_time_msec": 100,
            },
        )

    def track_session_context(self, *, groq: bool, football: bool, tavily: bool) -> None:
        self.track(
            "session_context",
            {
                "groq_ready": groq,
                "football_ready": football,
                "tavily_ready": tavily,
            },
            groq_configured=groq,
            football_configured=football,
            tavily_configured=tavily,
        )

    def track_briefing_requested(self, query_length: int) -> None:
        self.track("briefing_requested", {"query_length": query_length})

    def track_briefing_generated(self, result: dict) -> None:
        briefing = result.get("briefing") or ""
        self.track(
            "briefing_generated",
            {
                "team": result.get("team_name"),
                "team_corrected": bool(result.get("team_name_corrected")),
                "has_next_match": bool(result.get("next_match")),
                "briefing_chars": len(briefing),
            },
            focus_team=result.get("team_name"),
        )

    def track_briefing_error(self, category: str, detail: str = "") -> None:
        self.track(
            "briefing_error",
            {"error_category": category, "detail": detail[:120]},
        )

    def track_keys_missing(self, missing: list[str]) -> None:
        self.track(
            "keys_missing",
            {"missing_count": len(missing), "missing_keys": ",".join(missing)},
        )

    def track_setup_guide_download(self) -> None:
        self.track("setup_guide_download", {"asset": "api_keys_setup.docx"})

    def track_briefing_download(self, team: str | None) -> None:
        self.track("briefing_download", {"team": team, "format": "docx"})


_layer: StreamlitAnalytics | None = None


def get_analytics() -> StreamlitAnalytics:
    global _layer
    if _layer is None:
        _layer = StreamlitAnalytics()
    return _layer