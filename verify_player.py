"""Step 8 verification — run the player scout agent in isolation.

Run::

    uv run python verify_player.py

Or as in the PDF::

    PYTHONPATH=. uv run python -c "
    import asyncio
    from app.agents.player import player_node
    print(asyncio.run(player_node({'team_name': 'Brazil'}))['findings'][0].content)
    "

Expected: scouting text mentioning a real Brazilian player (e.g. Vinícius Júnior).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agents.player import player_node


async def go() -> None:
    """Run player_node for Brazil and print the Key Player finding."""
    result = await player_node({"team_name": "Brazil"})
    print(result["findings"][0].content)


if __name__ == "__main__":
    asyncio.run(go())