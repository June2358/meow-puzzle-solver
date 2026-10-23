"""Shared frame pacing for desktop pygame and Pygbag."""

import asyncio

import pygame

_TARGET_FRAME_RATE = 60


async def next_frame(clock: pygame.time.Clock) -> float:
    """Pace one frame, yield to the host event loop, and return elapsed seconds."""

    elapsed = clock.tick(_TARGET_FRAME_RATE) / 1000.0
    await asyncio.sleep(0)
    return elapsed
