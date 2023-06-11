from pathlib import Path
from typing import List
import pyter
import difflib

from metrics.types import MetricInput


class MetricEngine:
    def calculate(self, input: MetricInput, output_file_path: Path) -> float:
        diffs = difflib.context_diff(
            input.hypthesis_tokens,
            input.reference_tokens,
            fromfile="hypothesis",
            tofile="reference",
        )
        cdiff = "\n".join(diffs)
        output_file_path.write_text(cdiff)
        return pyter.ter(input.hypthesis_tokens, input.reference_tokens)
