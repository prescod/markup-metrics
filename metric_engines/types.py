from __future__ import annotations
from typing import TYPE_CHECKING, NamedTuple, Protocol, Sequence
from pathlib import Path

if TYPE_CHECKING:
    from markup_metrics.main import ProfileLogger


class MetricEngine(Protocol):
    unit: str
    name: str

    def calculate(self, input: MetricInput, output_file_dir: Path) -> float:
        ...


class MetricInput(NamedTuple):
    input_file: Path
    input_text: str
    hypothesis_text: str
    reference_text: str
    hypothesis_tokens: Sequence[str]
    reference_tokens: Sequence[str]
    profile_logger: ProfileLogger


class MetricOutput(NamedTuple):
    input_file: str
    input_text: str
    reference_text: str
    reference_tokens: str
    hypothesis_text: str
    hypothesis_tokens: str
