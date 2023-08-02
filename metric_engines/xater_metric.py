from pathlib import Path
from typing import List
import pyter
import difflib

from metric_engines.types import MetricInput


class MetricEngine:

    unit = "%"

    def calculate(self, input: MetricInput, output_file_dir: Path) -> float:
        with input.profile_logger.log_time("xater.difflib"):
            diffs = difflib.unified_diff(
                input.hypothesis_tokens,
                input.reference_tokens,
                fromfile="hypothesis",
                tofile="reference",
            )
        (output_file_dir / "hypothesis_tokenized.txt").write_text("\n".join(input.hypothesis_tokens))
        (output_file_dir / "referenced_tokenized.txt").write_text("\n".join(input.reference_tokens))
        cdiff = "\n".join(diffs)
        output_file_path = output_file_dir / "unified_diff.txt"
        output_file_path.write_text(cdiff)
        with input.profile_logger.log_time("xater.pyter"):
            ter = pyter.ter(input.hypothesis_tokens, input.reference_tokens)
            clamped_ter = clamp(ter, 0, 1)
            return 100 - clamped_ter * 100

def clamp(number, bottom, top):
    return max(bottom, min(number, top))
