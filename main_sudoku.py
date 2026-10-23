"""Pygbag-compatible application entry point."""

import asyncio

from puzzle_common.app import run_app
from sudoku.app import PLUGIN

if __name__ == "__main__":
    asyncio.run(run_app(PLUGIN))
