"""``python -m meow`` launches the pygame application."""

import asyncio

from puzzle_common.app import run_app

from .app import PLUGIN

if __name__ == "__main__":
    asyncio.run(run_app(PLUGIN))
