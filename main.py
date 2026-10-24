"""The single desktop and Pygbag entry point."""

import asyncio

import pygame  # noqa: F401  # Pygbag discovers its WebAssembly preload here.

from puzzle_common.app import run_app

if __name__ == "__main__":
    asyncio.run(run_app())
