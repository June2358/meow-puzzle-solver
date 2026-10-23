"""데스크톱 pygame과 Pygbag이 공유하는 프레임 속도 제어."""

import asyncio

import pygame

_TARGET_FRAME_RATE = 60


async def next_frame(clock: pygame.time.Clock) -> float:
    """프레임 속도를 조절하고 호스트 이벤트 루프에 양보한 뒤 경과 초를 반환한다."""

    elapsed = clock.tick(_TARGET_FRAME_RATE) / 1000.0
    await asyncio.sleep(0)
    return elapsed
