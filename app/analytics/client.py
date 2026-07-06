"""GA4 Measurement Protocol client — fire-and-forget, never raises to callers."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.analytics.settings import ANALYTICS, AnalyticsSettings

logger = logging.getLogger(__name__)

_COLLECT_URL = "https://www.google-analytics.com/mp/collect"
_VALIDATION_URL = "https://www.google-analytics.com/debug/mp/collect"


class AnalyticsClient:
    """Thin GA4 event sender. No-op when disabled or misconfigured."""

    def __init__(self, settings: AnalyticsSettings, *, client_id: str) -> None:
        self._settings = settings
        self._client_id = client_id

    @property
    def active(self) -> bool:
        return self._settings.active

    def track(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        *,
        user_properties: dict[str, Any] | None = None,
    ) -> None:
        if not self.active:
            return

        event: dict[str, Any] = {"name": name}
        if params:
            event["params"] = {k: v for k, v in params.items() if v is not None}

        body: dict[str, Any] = {
            "client_id": self._client_id,
            "events": [event],
        }
        if user_properties:
            body["user_properties"] = {
                key: {"value": value}
                for key, value in user_properties.items()
                if value is not None
            }

        query = {
            "measurement_id": self._settings.measurement_id,
            "api_secret": self._settings.api_secret,
        }

        try:
            with httpx.Client(timeout=2.5) as http:
                response = http.post(_COLLECT_URL, params=query, json=body)
                response.raise_for_status()
        except Exception as exc:
            logger.debug("GA event %s skipped: %s", name, exc)