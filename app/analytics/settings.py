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


@dataclass(frozen=True)
class AnalyticsSettings:
    """GA4 Measurement Protocol credentials and feature toggle."""

    enabled: bool
    measurement_id: str | None
    api_secret: str | None
    inject_client_tag: bool

    @property
    def server_active(self) -> bool:
        """Server-side Measurement Protocol (custom events)."""
        return self.enabled and bool(self.measurement_id and self.api_secret)

    @property
    def client_tag_active(self) -> bool:
        """Browser gtag.js — required for Google's tag detection wizard."""
        return self.enabled and bool(self.measurement_id) and self.inject_client_tag

    @property
    def active(self) -> bool:
        return self.server_active


ANALYTICS = AnalyticsSettings(
    enabled=_truthy(os.getenv("GA_ENABLED"), default=True),
    measurement_id=(os.getenv("GA_MEASUREMENT_ID") or "").strip() or None,
    api_secret=(os.getenv("GA_API_SECRET") or "").strip() or None,
    inject_client_tag=_truthy(os.getenv("GA_CLIENT_INJECT"), default=True),
)