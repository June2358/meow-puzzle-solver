"""Launch the shared app in Sudoku mode."""

import asyncio

from puzzle_common.app import run_app

if __name__ == "__main__":
    asyncio.run(run_app(initial_key="sudoku"))
