"""Step 4 — News client (beat journalist).

Official football data has scores but no narrative. RSS feeds need no key; Tavily
adds targeted search when configured. ``asyncio.gather`` fetches feeds in parallel.
"""

import asyncio

import feedparser
import httpx
from tavily import TavilyClient

from app.config import SETTINGS
from app.data.models import NewsItem
from app.data.results import ApiResult, explain_error, is_transient

RSS_FEEDS = {
    "BBC Football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Guardian Football": "https://www.theguardian.com/football/rss",
}


def _mentions(item: NewsItem, team: str) -> bool:
    """Keep only headlines that mention the focus team."""
    blob = f"{item.title} {item.summary or ''}".lower()
    return team.strip().lower() in blob


class NewsClient:
    """RSS headlines and optional Tavily web search for team storylines."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=15.0)

    async def __aenter__(self) -> "NewsClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self._http.aclose()

    async def _one_feed(self, source: str, url: str) -> list[NewsItem]:
        """Download and parse a single RSS feed."""
        try:
            response = await self._http.get(url)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)
            items: list[NewsItem] = []
            for entry in parsed.entries:
                items.append(
                    NewsItem(
                        source=source,
                        title=entry.get("title", ""),
                        link=entry.get("link"),
                        summary=(entry.get("summary") or "")[:300],
                    )
                )
            return items
        except Exception:
            return []

    async def fetch_rss(self, team: str, limit: int = 6) -> ApiResult[list[NewsItem]]:
        """Fetch RSS feeds in parallel and filter by team mention."""
        try:
            feeds = await asyncio.gather(
                *(self._one_feed(s, u) for s, u in RSS_FEEDS.items()),
                return_exceptions=True,
            )
            items = [i for feed in feeds if isinstance(feed, list) for i in feed]
            relevant = [i for i in items if _mentions(i, team)]
            return ApiResult(data=relevant[:limit])
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))

    async def search_tavily(self, team: str, opponent: str | None = None) -> ApiResult[list[NewsItem]]:
        """AI web search for fresh team news (skipped when no Tavily key)."""
        if not SETTINGS.has_tavily:
            return ApiResult(error="Tavily not configured")
        try:
            query = f"{team} World Cup news injuries lineup"
            if opponent:
                query = f"{team} vs {opponent} World Cup news"
            client = TavilyClient(api_key=SETTINGS.tavily_api_key)
            response = client.search(query=query, search_depth="advanced", max_results=5)
            items = [
                NewsItem(
                    source="Tavily",
                    title=r.get("title", ""),
                    link=r.get("url"),
                    summary=(r.get("content") or "")[:300],
                )
                for r in response.get("results", [])
            ]
            return ApiResult(data=items)
        except Exception as exc:
            return ApiResult(error=explain_error(exc), transient=is_transient(exc))