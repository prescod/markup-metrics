import argparse
from glob import glob
from pathlib import Path
from typing import List, Tuple

from prettytable import PrettyTable

from markup_metrics.profile_logger import ProfileLogger
from markup_metrics.tokenize_xml import tokenize_xml
from markup_metrics.utils import load_engine
from metric_engines.types import MetricEngine, MetricInput

from .utils import setup_catalog_env_var


## TODO: Fix this code


def calculate_metrics(
    datadir: Path, engines: List[MetricEngine], prof_log: ProfileLogger, out: Path
) -> List[Tuple[str, str, str, float]]:
    results = []
    for ref_file in datadir.rglob("*reference.xml"):
        ref_results = process_reference_set(
            ref_file, ref_file.parent, engines, prof_log, out
        )
        results.extend(ref_results)
    return results


def process_reference_set(
    ref_file: Path,
    datadir: Path,
    engines: List[MetricEngine],
    prof_log: ProfileLogger,
    out: Path,
) -> List[Tuple[str, str, str, float]]:
    ref_stem = ref_file.stem.split(".")[0]
    results = []
    for test_file in Path(datadir).glob(f"{ref_stem}.*.xml"):
        if test_file.stem != ref_file.stem:
            for engine in engines:
                test_data = test_file.read_text()
                reference_text = ref_file.read_text()
                input = MetricInput(
                    test_file,
                    ref_file.read_text(),
                    test_data,
                    reference_text,
                    tokenize_xml(test_data),
                    tokenize_xml(reference_text),
                    profile_logger=prof_log,
                )

                # Create a new path for the output file based on the "out" path and the name of the test file
                output_file_path = out / (test_file.name + ".out")
                output_file_path.mkdir(parents=True, exist_ok=True)
                score = engine.calculate(input, output_file_path)
                results.append((str(ref_file), test_file.name, engine.name, score))
    return results


def main():
    parser = argparse.ArgumentParser(description="Test metrics against test cases.")
    parser.add_argument(
        "--metric-engines",
        type=str,
        default="metrics/*_metric.py",
        help="Glob pattern for the scripts containing the MetricEngine classes.",
    )
    parser.add_argument(
        "--datadir",
        type=str,
        default="./test_metrics/",
        help="Path to the data directory.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="./out/test_metrics",
        help="Path to the output directory.",
    )

    args = parser.parse_args()
    metric_engine_scripts = glob(args.metric_engines)
    metric_engines = [
        load_engine(metric_engine_script, "MetricEngine")
        for metric_engine_script in metric_engine_scripts
    ]
    metric_engines = [engine for engine in metric_engines if engine is not None]

    # Add a check if no metrics are found
    if not metric_engines:
        raise ValueError(
            "No metrics were found. Please check the --metric-engines argument."
        )

    # Add a check if no data is found
    data_files = list(Path(args.datadir).rglob("*reference.xml"))
    if not data_files:
        raise ValueError(
            f"No data files were found in the directory {args.datadir}. Please check the --datadir argument."
        )
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    proflog = ProfileLogger()
    setup_catalog_env_var()
    results = calculate_metrics(Path(args.datadir), metric_engines, proflog, outdir)

    table = PrettyTable(["Reference File", "Test File", "Engine", "Score"])
    for row in results:
        table.add_row(row)
    print(table)
    print("Detailed information in", outdir)


if __name__ == "__main__":
    main()
