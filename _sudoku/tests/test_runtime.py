import asyncio

import pytest

import sudoku.runtime as runtime


def test_next_frame_caps_cpu_and_yields_to_the_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tick_calls: list[int] = []
    sleep_calls: list[int] = []

    class FakeClock:
        def tick(self, frame_rate: int) -> int:
            tick_calls.append(frame_rate)
            return 25

    async def fake_sleep(delay: int) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(runtime.asyncio, "sleep", fake_sleep)

    elapsed = asyncio.run(runtime.next_frame(FakeClock()))

    assert elapsed == 0.025
    assert tick_calls == [60]
    assert sleep_calls == [0]
