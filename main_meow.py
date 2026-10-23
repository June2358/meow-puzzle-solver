"""Pygbag-compatible application entry point."""

import asyncio

from meow.app import PLUGIN
from puzzle_common.app import run_app

if __name__ == "__main__":
    asyncio.run(run_app(PLUGIN))
