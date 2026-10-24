"""Pygbag-compatible application entry point."""

import asyncio

import pygame  # noqa: F401  # Pygbag preloads the WebAssembly module from this import.

from meow.app import PLUGIN
from puzzle_common.app import run_app

if __name__ == "__main__":
    asyncio.run(run_app(PLUGIN))
