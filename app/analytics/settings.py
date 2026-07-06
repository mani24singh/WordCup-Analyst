"""Google Analytics 4 configuration — optional, env-driven, fully detachable."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _truthy(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _lookup(key: str) -> str | None:
    """Read from os.environ first, then Streamlit Cloud secrets."""
    env_val = os.getenv(key)
    if env_val is not None and str(env_val).strip():
        return str(env_val).strip()
    try:
        import streamlit as st

        if key in st.secrets:
            raw = st.secrets[key]
            if raw is not None and str(raw).strip():
                return str(raw).strip()
    except Exception:
        pass
    return None


@dataclass(frozen=True)
class AnalyticsSettings:
    """GA4 Measurement Protocol credentials and feature toggle."""

    enabled: bool
    measurement_id: str | None
    api_secret: str | None
    inject_client_tag: bool
    debug: bool
    app_url: str

    @property
    def server_active(self) -> bool:
        """Server-side Measurement Protocol (custom events)."""
        return self.enabled and bool(self.measurement_id and self.api_secret)

    @property
    def client_tag_active(self) -> bool:
        """Browser gtag.js — optional; Streamlit wizard detection often still fails."""
        return self.enabled and bool(self.measurement_id) and self.inject_client_tag

    @property
    def active(self) -> bool:
        return self.server_active


def load_analytics_settings() -> AnalyticsSettings:
    """Load GA settings on each request (Streamlit secrets are not available at import)."""
    return AnalyticsSettings(
        enabled=_truthy(_lookup("GA_ENABLED"), default=True),
        measurement_id=_lookup("GA_MEASUREMENT_ID"),
        api_secret=_lookup("GA_API_SECRET"),
        inject_client_tag=_truthy(_lookup("GA_CLIENT_INJECT"), default=True),
        debug=_truthy(_lookup("GA_DEBUG"), default=False),
        app_url=_lookup("GA_APP_URL")
        or "https://wordcup-analyst-2026.streamlit.app/",
    )


def get_analytics_settings() -> AnalyticsSettings:
    return load_analytics_settings()