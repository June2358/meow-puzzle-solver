"""Browser access and frame pacing for desktop pygame and WebAssembly."""

import asyncio
import sys

import pygame

_TARGET_FRAME_RATE = 60


def browser_window():  # noqa: ANN202
    from js import window

    return window


def browser_viewport() -> tuple[int, int] | None:
    if sys.platform != "emscripten":
        return None
    try:
        window = browser_window()
        width, height = int(window.innerWidth), int(window.innerHeight)
        return (width, height) if width > 0 and height > 0 else None
    except AttributeError, ImportError, TypeError, ValueError:
        return None


async def next_frame(clock: pygame.time.Clock) -> float:
    """Pace one frame, yield to the host event loop, and return elapsed seconds."""

    if sys.platform == "emscripten":
        # SDL delays block Pyodide's main thread; let the browser pace frames.
        await asyncio.sleep(1 / _TARGET_FRAME_RATE)
        return clock.tick() / 1000.0
    elapsed = clock.tick(_TARGET_FRAME_RATE) / 1000.0
    await asyncio.sleep(0)
    return elapsed
