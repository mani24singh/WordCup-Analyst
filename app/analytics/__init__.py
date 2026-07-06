"""Optional Google Analytics layer — safe to remove from the project."""

from app.analytics.settings import ANALYTICS
from app.analytics.streamlit_bridge import StreamlitAnalytics, get_analytics

__all__ = ["ANALYTICS", "StreamlitAnalytics", "get_analytics"]