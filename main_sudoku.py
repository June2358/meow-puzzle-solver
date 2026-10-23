"""Pygbag-compatible application entry point."""

import asyncio

from sudoku.app import main

if __name__ == "__main__":
    asyncio.run(main())
