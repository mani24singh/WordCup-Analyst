"""Streamlit-facing analytics layer — import only from streamlit_app.py."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.analytics.client import AnalyticsClient
from app.analytics.gtag import gtag_fragment_html, parent_frame_gtag_html
from app.analytics.settings import AnalyticsSettings, load_analytics_settings

logger = logging.getLogger(__name__)


class StreamlitAnalytics:
    """
    Detachable analytics facade for the Streamlit UI.

    Primary data path: Measurement Protocol (needs GA_MEASUREMENT_ID + GA_API_SECRET).
    Browser gtag is optional; Google's tag wizard often fails on Streamlit anyway.
    """

    def __init__(self) -> None:
        self.reload_settings()

    def reload_settings(self) -> None:
        self._settings = load_analytics_settings()

    @property
    def active(self) -> bool:
        return self._settings.server_active

    @property
    def debug_enabled(self) -> bool:
        return self._settings.debug

    @property
    def client_tag_enabled(self) -> bool:
        return self._settings.client_tag_active

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
        debug = self._settings.debug
        result = self._client().track(
            name,
            params,
            user_properties=user_props or None,
            debug=debug,
        )
        if debug:
            st.session_state["_ga_last_event"] = name
            st.session_state["_ga_last_debug"] = result
            messages = (result or {}).get("validationMessages") or []
            st.session_state["_ga_last_ok"] = not messages

    def inject_client_tag(self) -> None:
        """Optional gtag inject — not required for Measurement Protocol events."""
        if not self._settings.client_tag_active:
            return

        mid = self._settings.measurement_id or ""
        full = parent_frame_gtag_html(mid)
        if not full:
            return

        injected = False

        if hasattr(st, "html"):
            try:
                st.html(full)
                injected = True
            except Exception as exc:
                logger.debug("st.html gtag inject failed: %s", exc)

        if not injected:
            try:
                components.html(full, height=1, width=1)
                injected = True
            except TypeError:
                components.html(full, height=1)
            except Exception as exc:
                logger.debug("components.html full gtag inject failed: %s", exc)

        if not injected:
            fragment = gtag_fragment_html(mid)
            if fragment:
                try:
                    components.html(fragment, height=1, width=1)
                except Exception as exc:
                    logger.debug("components.html fragment gtag inject failed: %s", exc)

        st.session_state["_ga_tag_injected"] = injected

    def debug_status(self) -> str | None:
        """Status line for sidebar when GA_DEBUG=true."""
        if not self._settings.enabled:
            return "GA disabled (GA_ENABLED=false)"
        mid = self._settings.measurement_id
        if not mid:
            return "GA_MEASUREMENT_ID missing — add to Streamlit Secrets and reboot"
        secret = self._settings.api_secret
        if not secret:
            return f"ID {mid[:8]}… · MP off — set GA_API_SECRET in Secrets and reboot"

        parts = [f"ID {mid[:8]}…", "MP on"]
        if self._settings.client_tag_active:
            parts.append("gtag on" if st.session_state.get("_ga_tag_injected") else "gtag inject pending")
        if st.session_state.get("_ga_last_event"):
            ok = st.session_state.get("_ga_last_ok")
            parts.append(
                f"last {st.session_state['_ga_last_event']} "
                + ("ok" if ok else "FAILED")
            )
        return " · ".join(parts)

    def debug_detail(self) -> str | None:
        """Validation messages from the debug MP endpoint."""
        payload = st.session_state.get("_ga_last_debug")
        if not payload:
            return None
        messages = payload.get("validationMessages") or []
        if not messages:
            return "Last event validated OK (check GA4 → Realtime within 30s)"
        lines = []
        for msg in messages[:5]:
            if isinstance(msg, dict):
                lines.append(msg.get("description") or str(msg))
            else:
                lines.append(str(msg))
        return "; ".join(lines)

    def _page_location(self) -> str:
        return self._settings.app_url.rstrip("/") + "/"

    def track_page_view(self) -> None:
        self.track(
            "page_view",
            {
                "page_title": "WorldCup Analyst",
                "page_location": self._page_location(),
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
    else:
        _layer.reload_settings()
    return _layer