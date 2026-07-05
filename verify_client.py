"""Step 3 verification — confirm football-data.org client works.

Run::

    uv run python verify_client.py

Expected output::

    Brazil id: 764
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.data.client import FootballDataClient


async def go() -> None:
    """Resolve Brazil's team id via the async context manager."""
    async with FootballDataClient() as c:
        r = await c.resolve_team_id("Brazil")
        print("Brazil id:", r.data.id if r.ok else r.error)


if __name__ == "__main__":
    asyncio.run(go())