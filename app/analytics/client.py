"""GA4 Measurement Protocol client — fire-and-forget, never raises to callers."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.analytics.settings import AnalyticsSettings

logger = logging.getLogger(__name__)

_COLLECT_URL = "https://www.google-analytics.com/mp/collect"
_VALIDATION_URL = "https://www.google-analytics.com/debug/mp/collect"
_MAX_PARAM_LEN = 500


def _sanitize_value(value: Any) -> str | int | float:
    """GA4 MP accepts only strings and numbers — booleans are rejected."""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value[:_MAX_PARAM_LEN]
    text = str(value)
    return text[:_MAX_PARAM_LEN]


def _sanitize_map(data: dict[str, Any]) -> dict[str, str | int | float]:
    return {key: _sanitize_value(val) for key, val in data.items() if val is not None}


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
        debug: bool = False,
    ) -> dict[str, Any] | None:
        if not self.active:
            return None

        event: dict[str, Any] = {"name": name}
        if params:
            event["params"] = _sanitize_map(params)

        body: dict[str, Any] = {
            "client_id": self._client_id,
            "events": [event],
        }
        if user_properties:
            body["user_properties"] = {
                key: {"value": _sanitize_value(value)}
                for key, value in user_properties.items()
                if value is not None
            }

        query = {
            "measurement_id": self._settings.measurement_id,
            "api_secret": self._settings.api_secret,
        }
        url = _VALIDATION_URL if debug else _COLLECT_URL

        try:
            with httpx.Client(timeout=5.0) as http:
                response = http.post(url, params=query, json=body)
                response.raise_for_status()
                if debug:
                    return response.json()
        except Exception as exc:
            if debug:
                return {"validationMessages": [{"description": str(exc)}]}
            logger.debug("GA event %s skipped: %s", name, exc)
        return None