import asyncio
from types import SimpleNamespace

import pytest

import puzzle_common.runtime as runtime


@pytest.mark.parametrize("platform", ("win32", "emscripten"))
def test_next_frame_caps_cpu_without_blocking_the_browser(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
) -> None:
    tick_calls: list[int] = []
    sleep_calls: list[float] = []

    class FakeClock:
        def tick(self, frame_rate: int = 0) -> int:
            tick_calls.append(frame_rate)
            return 25

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(runtime.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(
        runtime, "sys", SimpleNamespace(platform=platform), raising=False
    )

    elapsed = asyncio.run(runtime.next_frame(FakeClock()))

    assert elapsed == 0.025
    assert tick_calls == ([0] if platform == "emscripten" else [60])
    assert sleep_calls == ([1 / 60] if platform == "emscripten" else [0])
