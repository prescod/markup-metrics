from typing import NamedTuple, Sequence


class MetricInput(NamedTuple):
    hypothesis_text: str
    reference_text: str
    hypthesis_tokens: Sequence[str]
    reference_tokens: Sequence[str]
