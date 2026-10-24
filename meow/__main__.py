"""Launch the shared app in MEOW mode."""

import asyncio

from puzzle_common.app import run_app

if __name__ == "__main__":
    asyncio.run(run_app(initial_key="meow"))
