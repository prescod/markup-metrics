from __future__ import annotations
from typing import TYPE_CHECKING, NamedTuple, Protocol, Sequence

if TYPE_CHECKING:
    from markup_metrics.main import ProfileLogger

class MetricEngine(Protocol):
    unit: str
    name: str

    def calculate(self, input: MetricInput, output_file_dir: Path) -> float:
        ...


class MetricInput(NamedTuple):
    hypothesis_text: str
    reference_text: str
    hypothesis_tokens: Sequence[str]
    reference_tokens: Sequence[str]
    profile_logger: ProfileLogger
