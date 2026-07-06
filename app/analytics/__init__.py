"""Optional Google Analytics layer — safe to remove from the project."""

from app.analytics.settings import get_analytics_settings, load_analytics_settings
from app.analytics.streamlit_bridge import StreamlitAnalytics, get_analytics

__all__ = [
    "StreamlitAnalytics",
    "get_analytics",
    "get_analytics_settings",
    "load_analytics_settings",
]