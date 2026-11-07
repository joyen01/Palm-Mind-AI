"""Generic helpers for splitting work into fixed-size batches."""

from collections.abc import Iterator, Sequence


def batched[T](items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield consecutive slices of ``items`` holding at most ``size`` elements each."""
    if size <= 0:
        raise ValueError("Batch size must be positive.")
    for start in range(0, len(items), size):
        yield items[start : start + size]
