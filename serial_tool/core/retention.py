"""Capacity reclamation policy.

Only computes "how many blocks to drop from the head"; the document itself is
untouched, so the caller can delete whole blocks and keep all formatting
(colors, timestamps, highlights) of the remaining content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

DEFAULT_KEEP_RATIO = 0.7


@dataclass(frozen=True)
class TrimPlan:
    delete_blocks: int
    keep_blocks: int


def trim_plan(
    block_chars: Sequence[int],
    limit_chars: int,
    keep_ratio: float = DEFAULT_KEEP_RATIO,
) -> TrimPlan:
    """Decide how many blocks need to be deleted.

    Returns 0 when under the limit; when over, accumulate from the tail backwards
    and keep roughly limit*keep_ratio of content, always keeping at least one
    block (so the line just received is never dropped).
    """
    blocks = list(block_chars)
    total = sum(blocks)

    if not blocks or total <= limit_chars:
        return TrimPlan(0, len(blocks))

    if limit_chars <= 0:
        return TrimPlan(len(blocks) - 1, 1)

    target = limit_chars * keep_ratio
    kept = 0
    accumulated = 0
    for size in reversed(blocks):
        accumulated += size
        kept += 1
        if accumulated >= target:
            break

    kept = max(1, kept)
    return TrimPlan(len(blocks) - kept, kept)
