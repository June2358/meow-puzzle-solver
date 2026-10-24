"""Launch the shared puzzle application with its selection screen."""

import asyncio

from .app import run_app

if __name__ == "__main__":
    asyncio.run(run_app())
