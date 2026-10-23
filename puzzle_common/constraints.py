"""Shared locked-candidate confinement and target selection."""

from collections.abc import Callable, Collection, Sequence


def locked_candidate_targets[Cell](
    source: Collection[Cell],
    evidence: Sequence[Cell],
    target_units: Sequence[Sequence[Cell]],
    target_index: Callable[[Cell], int],
    is_possible: Callable[[Cell], bool],
) -> tuple[int, tuple[Cell, ...]] | None:
    """Find possible cells outside a source when its evidence shares one target."""

    indices = {target_index(cell) for cell in evidence}
    if len(indices) != 1:
        return None
    index = min(indices)
    targets = tuple(
        cell for cell in target_units[index] if cell not in source and is_possible(cell)
    )
    return (index, targets) if targets else None
