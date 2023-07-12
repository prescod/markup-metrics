from __future__ import annotations
from typing import TYPE_CHECKING, NamedTuple, Sequence

if TYPE_CHECKING:
    from markup_metrics.main import ProfileLogger


class MetricInput(NamedTuple):
    hypothesis_text: str
    reference_text: str
    hypothesis_tokens: Sequence[str]
    reference_tokens: Sequence[str]
    profile_logger: ProfileLogger
