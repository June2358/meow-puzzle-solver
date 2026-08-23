"""``python -m meow`` launches the pygame application."""

import asyncio

from .app import main

if __name__ == "__main__":
    asyncio.run(main())
