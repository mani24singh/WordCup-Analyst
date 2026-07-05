"""Step 1 — Configuration and the two-model strategy.

Groq's free tier counts token budgets per model. The 70b model has a small daily
budget; the 8b model has a much larger one. Agents use the cheap model for tool
loops; only the final reader-facing synthesis uses the 70b model.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()  # read .env into the environment before anything else

LIGHT_MODEL = "llama-3.1-8b-instant"  # router + agent tool-loops
HEAVY_MODEL = "llama-3.3-70b-versatile"  # final synthesis only


@dataclass
class Settings:
    """Application secrets loaded from the environment."""

    groq_api_key: str | None
    football_token: str | None
    tavily_api_key: str | None

    @property
    def has_tavily(self) -> bool:
        """True when Tavily search is configured (optional third data source)."""
        return bool(self.tavily_api_key)


SETTINGS = Settings(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    football_token=os.getenv("FOOTBALL_DATA_TOKEN"),
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
)


def apply_settings(
    *,
    groq_api_key: str | None = None,
    football_token: str | None = None,
    tavily_api_key: str | None = None,
) -> None:
    """Override SETTINGS at runtime (e.g. from Streamlit sidebar inputs)."""
    if groq_api_key is not None:
        SETTINGS.groq_api_key = groq_api_key or None
        os.environ["GROQ_API_KEY"] = groq_api_key
    if football_token is not None:
        SETTINGS.football_token = football_token or None
        os.environ["FOOTBALL_DATA_TOKEN"] = football_token
    if tavily_api_key is not None:
        SETTINGS.tavily_api_key = tavily_api_key or None
        os.environ["TAVILY_API_KEY"] = tavily_api_key


def agent_model() -> ChatGroq:
    """The cheap 8b model that drives the agents' tool loops."""
    return ChatGroq(
        model=LIGHT_MODEL,
        api_key=SETTINGS.groq_api_key,
        temperature=0.0,  # deterministic tool decisions
    )


def light_model() -> ChatGroq:
    """The 8b router model used by the supervisor for structured routing."""
    return agent_model()


def heavy_model() -> ChatGroq:
    """The 70b model for the final reader-facing synthesis."""
    return ChatGroq(
        model=HEAVY_MODEL,
        api_key=SETTINGS.groq_api_key,
        temperature=0.3,  # slight variety for natural prose
    )