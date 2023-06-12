from pathlib import Path
from typing import List
import pyter
import difflib
from markup_metrics.main import ProfileLog

from metrics.types import MetricInput


class MetricEngine:

    unit = "%"

    def calculate(self, input: MetricInput, output_file_dir: Path) -> float:
        with input.profile_logger.log_time("xater.difflib"):
            diffs = difflib.unified_diff(
                input.hypthesis_tokens,
                input.reference_tokens,
                fromfile="hypothesis",
                tofile="reference",
            )
        cdiff = "\n".join(diffs)
        output_file_path = output_file_dir / "unified_diff.txt"
        output_file_path.write_text(cdiff)
        with input.profile_logger.log_time("xater.pyter"):
            return pyter.ter(input.hypthesis_tokens, input.reference_tokens) * 100
