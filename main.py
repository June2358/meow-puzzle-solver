"""Pygbag과 호환되는 앱 진입점."""

import asyncio

from sudoku.app import main

if __name__ == "__main__":
    asyncio.run(main())
