from __future__ import annotations

import pytest

from meow.model import Puzzle


@pytest.fixture(scope="session")
def stalled_probe_puzzle() -> Puzzle:
    """새 CAT 후보가 모두 정지한 뒤 탐색이 필요한 복수해 퍼즐."""

    return Puzzle.from_region_grid(
        (
            tuple("BDDDDDAAAAA"),
            tuple("BBDDDCCAAAA"),
            tuple("BBDDCCCCCAA"),
            tuple("BBDDDDCCCEA"),
            tuple("BDDDDDCEEEE"),
            tuple("BDGGDFCIEEE"),
            tuple("GGGGDIIIEII"),
            tuple("JGGHHIIIIII"),
            tuple("JJGHHHIIIII"),
            tuple("JJHHHIIIKKK"),
            tuple("JHHHHHKKKKK"),
        )
    )
