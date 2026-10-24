"""Shared candidate confinement and matching feasibility."""

from collections.abc import Callable, Collection, Sequence


def has_distinct_representatives(domains: tuple[int, ...]) -> bool:
    """Match every bitmask domain to a distinct bit in polynomial time."""
    assigned: dict[int, int] = {}

    def augment(source: int, seen: set[int]) -> bool:
        remaining = domains[source]
        while remaining:
            target = remaining & -remaining
            remaining ^= target
            if target in seen:
                continue
            seen.add(target)
            previous = assigned.get(target)
            if previous is None or augment(previous, seen):
                assigned[target] = source
                return True
        return False

    return all(augment(source, set()) for source in range(len(domains)))


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
