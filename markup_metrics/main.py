import argparse
import csv
from fnmatch import fnmatch
import glob
from pyexpat import ExpatError
import shutil
import statistics
import time
from pathlib import Path
import traceback
from typing import (
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    cast,
)
from xml.etree.ElementTree import parse
from xml.sax import SAXParseException
import yaml

from prettytable import PrettyTable

from markup_engines.types import MarkupEngine, Tokenizer as TokenizerProtocol
from markup_metrics.profile_logger import ProfileLogger
from markup_metrics.tokenize_xml import XMLTokenizer
from metric_engines.types import MetricInput, MetricEngine

from .utils import load_engine, setup_catalog_env_var


class LogResult(NamedTuple):
    input_file: str
    markup_engine: str
    metric_engine: str
    score: float
    unit: str
    input_text: str
    hypothesis_text: str
    reference_text: str


class SimpleLogger:
    def __init__(self, filename: Path) -> None:
        self.file = filename.open("w")
        self._results = []

    def log(self, *message: str) -> None:
        joined = " ".join(str(m) for m in message)
        self.file.write(joined + "\n")
        self.file.flush()
        print(joined)

    def log_result(self, row):
        self._results.append(row)


class Config(NamedTuple):
    automarkup_engine_scripts: list[str]
    metric_engine_scripts: list[str]
    datadir: Path
    outdir: Path
    tokenizer: TokenizerProtocol
    logger: SimpleLogger
    prof_logger: ProfileLogger
    filter_list: Optional[List[str]]
    operation: str  # maybe this should be inferred from the engine instead
    halt_on_error: bool
    save_as_test_cases: bool = False


def parse_prompt(schema_dir: Path) -> str:
    prompt_path = schema_dir / "prompt.txt"
    if prompt_path.exists():
        with prompt_path.open("r") as file:
            return file.read()
    else:
        return ""


def parse_reference_text(
    xml_path: Path, tokenizer: TokenizerProtocol, logger: SimpleLogger
) -> Optional[str]:
    try:
        with xml_path.open("r") as file:
            reference_text = file.read()
            tokenizer.tokenize(reference_text)
            return reference_text
    except SAXParseException:
        logger.log(f"Error: XML parsing failed for {xml_path}")
        return None


def process_file(
    txt_path: Path,
    automarkup,
    metric_engine,
    prompt: str,
    engine_outdir: Path,
    config: Config,
) -> Tuple[float, bool, Optional[Path], Optional[MetricInput]]:
    if config.operation:
        extension = f"{config.operation}.xml"
    else:
        extension = "xml"

    xml_paths = list(txt_path.parent.glob(f"{txt_path.stem}.{extension}")) + list(
        txt_path.parent.glob(f"{txt_path.stem}.[0-9]*.{extension}")
    )

    # save the output of the markup engines as test cases if there are none
    if config.save_as_test_cases and not xml_paths:
        automarkup_output = automarkup.automarkup(txt_path.read_text(), prompt)
        (txt_path.parent / f"{txt_path.stem}.{extension}").write_text(automarkup_output)

    try:
        output_file_path, output_text = do_automarkup(
            txt_path, prompt, engine_outdir, automarkup, config
        )
    except (UnicodeDecodeError, SAXParseException, ExpatError, ValueError) as e:
        config.logger.log(f"            Error: {e} for {txt_path}")
        return (0, False, None, None)

    results = [
        compare_with_reference_safe(
            xml_path,
            txt_path,
            metric_engine,
            output_file_path,
            output_text,
            config,
        )
        for xml_path in xml_paths
    ]
    return max(results) if results else (0, False, None, None)


def compare_with_reference_safe(
    xml_path,
    txt_path,
    metric_engine,
    output_file_path,
    output_text,
    config,
) -> Tuple[float, bool, Optional[Path], Optional[MetricInput]]:
    try:
        result = compare_with_reference(
            xml_path,
            txt_path,
            metric_engine,
            output_file_path,
            output_text,
            config,
        )
    except Exception as e:
        if config.halt_on_error:
            raise e
        config.logger.log(f"            Error: {e}")
        traceback.print_exc()
        result = 0, False, None, None
    return result


counter = 0


def compare_with_reference(
    xml_path: Path,
    txt_path: Path,
    metric_engine,
    output_file_path: Path,
    output_text: str,
    config: Config,
) -> Tuple[float, bool, Optional[Path], Optional[MetricInput]]:
    reference_text = parse_reference_text(xml_path, config.tokenizer, config.logger)
    if reference_text is None:
        return 0, False, None, None

    try:
        config.tokenizer.tokenize(output_text)
    except SAXParseException as e:
        config.logger.log(
            f"            Error: XML parsing failed for output, saved to {output_file_path} : {e}"
        )
        return 0, False, None, None

    validator_input = MetricInput(
        txt_path,
        txt_path.read_text(),
        output_text,
        reference_text,
        config.tokenizer.tokenize(output_text),
        config.tokenizer.tokenize(reference_text),
        profile_logger=config.prof_logger,
    )
    metric_output = Path(f"{output_file_path}__{metric_engine.name}")
    if metric_output.exists():
        shutil.rmtree(metric_output)

    metric_output.mkdir(parents=True, exist_ok=True)
    with config.prof_logger.log_time(f"{metric_engine.name} for : {txt_path}"):
        score = metric_engine.calculate(validator_input, metric_output)
        output_report = metric_output / "report.yml"
        output_report.write_text(
            yaml.dump(
                {
                    "input_file": str(validator_input.input_file.absolute()),
                    "input_text": validator_input.input_text,
                    "reference_text": validator_input.reference_text,
                    "hypothesis_text": validator_input.hypothesis_text,
                    "hypothesis_tokens": validator_input.hypothesis_tokens,
                    "reference_tokens": validator_input.reference_tokens,
                }
            )
        )

    return score, True, output_file_path, validator_input


def do_automarkup(
    txt_path: Path,
    prompt: str,
    engine_outdir: Path,
    automarkup: MarkupEngine,
    config: Config,
):
    with txt_path.open("r") as file:
        input_text = file.read()
    with config.prof_logger.log_time(f"{automarkup.name} for: {txt_path}"):
        global counter
        counter += 1
        output_text = automarkup.automarkup(input_text, prompt)
    relative_path = txt_path.relative_to(txt_path.parent.parent)
    output_file_path = (
        engine_outdir
        / relative_path.parent
        / txt_path.stem
        / (txt_path.stem + config.operation + ".xml")
    )
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with output_file_path.open("w") as output_file:
        output_file.write(output_text)

    return output_file_path, output_text


def process_schema_directory(
    schema_dir: Path,
    automarkup: MarkupEngine,
    metric_engine: MetricEngine,
    engine_outdir: Path,
    config: Config,
) -> Tuple[float, int, list]:
    prompt = parse_prompt(schema_dir)
    score_sum = 0
    file_count = 0
    errors = []

    config.logger.log(f"     {schema_dir.stem}")

    filter_list = config.filter_list or ["*.txt"]

    for txt_path in schema_dir.glob("*.txt"):
        pattern_matches = any(
            fnmatch(str(txt_path.absolute()), "*/" + f) for f in filter_list
        )
        if txt_path.stem != "prompt" and pattern_matches:
            score, success, output_file, metric_input = process_file(
                txt_path,
                automarkup,
                metric_engine,
                prompt,
                engine_outdir,
                config,
            )
            if success:
                file_count += 1
                score_sum += score
                short_path = txt_path.relative_to(schema_dir.parent)
                config.logger.log(
                    f"            {short_path} ({output_file}): {score:.2f}{metric_engine.unit}"
                )
                config.logger.log_result(
                    LogResult(
                        str(short_path),
                        automarkup.name,
                        metric_engine.name,
                        score,
                        metric_engine.unit,
                        metric_input.input_text if metric_input else "",
                        metric_input.hypothesis_text if metric_input else "",
                        metric_input.reference_text if metric_input else "",
                    )
                )
            else:
                errors.append([txt_path, output_file])

    return score_sum, file_count, errors


# Protocol for engines
class Engine(Protocol):
    name: str


# NamedTuple for schema score
class SchemaScore(NamedTuple):
    schema_name: str
    average_score: float


# NamedTuple for the result of processing a combination
class ProcessingResult(NamedTuple):
    markup_engine_name: str
    metric_engine_name: str
    schema_scores: List[SchemaScore]


def process_automarkup_metric_combination(
    markup_engine: MarkupEngine, metric_engine: MetricEngine, config: Config
) -> ProcessingResult:
    engine_outdir = config.outdir / markup_engine.name
    if hasattr(markup_engine, "output_parameters"):
        engine_outdir.mkdir(parents=True, exist_ok=True)
        markup_engine.output_parameters(engine_outdir)

    schema_scores = []
    errors = []

    for schema_dir in config.datadir.rglob("*"):
        if schema_dir.is_dir():
            schema_name = schema_dir.stem

            score_sum, file_count, schema_errors = process_schema_directory(
                schema_dir,
                markup_engine,
                metric_engine,
                engine_outdir,
                config,
            )
            errors.extend(schema_errors)

            if file_count > 0:
                average_score = score_sum / file_count
                schema_scores.append(SchemaScore(schema_name, average_score))

    return ProcessingResult(markup_engine.name, metric_engine.name, schema_scores)


def generate_results(config: Config):
    markup_engines = [
        load_engine(automarkup_engine_script, "AutoMarkup")
        for automarkup_engine_script in config.automarkup_engine_scripts
    ]
    markup_engines = [
        markup_engine for markup_engine in markup_engines if markup_engine is not None
    ]

    metric_engines = [
        load_engine(metric_engine_script, "MetricEngine")
        for metric_engine_script in config.metric_engine_scripts
    ]
    metric_engines = [
        metric_engine for metric_engine in metric_engines if metric_engine is not None
    ]

    table_data = []

    for markup_engine in markup_engines:
        for metric_engine in metric_engines:
            config.logger.log(
                f"Processing {markup_engine.name} with {metric_engine.name}"
            )

            result = process_automarkup_metric_combination(
                markup_engine,
                metric_engine,
                config,
            )

            for schema_score in result.schema_scores:
                table_data.append(
                    {
                        "Markup Engine": result.markup_engine_name,
                        "Metric Engine": result.metric_engine_name,
                        "Schema Name": schema_score.schema_name,
                        "Average Score": f"{schema_score.average_score:.2f}{metric_engine.unit}",
                    }
                )

            if result.schema_scores:
                overall_average = statistics.mean(
                    score.average_score for score in result.schema_scores
                )
                table_data.append(
                    {
                        "Markup Engine": result.markup_engine_name,
                        "Metric Engine": result.metric_engine_name,
                        "Schema Name": "Overall Average",
                        "Average Score": f"{overall_average:.2f}{metric_engine.unit}",
                    }
                )

    # Output the data in table format
    if table_data:
        table = PrettyTable()
        table.field_names = [
            "Markup Engine",
            "Metric Engine",
            "Schema Name",
            "Average Score",
        ]
        for row in table_data:
            table.add_row(
                [
                    row["Markup Engine"],
                    row["Metric Engine"],
                    row["Schema Name"],
                    row["Average Score"],
                ]
            )
        config.logger.log(str(table))

    log_file_path = config.outdir / "time_logs.txt"
    with log_file_path.open("w") as log_file:
        log_file.write("Context\tTime (s)\tCalls\n")
        for log in config.prof_logger.times:
            log_file.write(f"{log.name}\t{log.time:.6f}\n")

    with open(config.outdir / "results.csv", "w") as results_file:
        csv_writer = csv.DictWriter(
            results_file, config.logger._results[0]._asdict().keys()
        )
        csv_writer.writeheader()
        csv_writer.writerows(r._asdict() for r in config.logger._results)


class CharacterTokenizer(TokenizerProtocol):
    def tokenize(self, text: str) -> list[str]:
        return list(text)


class ArgumentParseError(Exception):
    pass


def parse_args() -> Config:
    pkg_root = str(Path(__file__).parent.parent)
    parser = argparse.ArgumentParser(description="Evaluate markup script.")
    parser.add_argument(
        "--automarkup-engines",
        type=str,
        default=f"{pkg_root}/markup_engines/*_automarkup.py",
        help="Glob pattern for the scripts containing the AutoMarkup classes.",
    )
    parser.add_argument(
        "--metric-engines",
        type=str,
        default=f"{pkg_root}/metric_engines/*_metric.py",
        help="Glob pattern for the scripts containing the MetricEngine classes.",
    )
    parser.add_argument(
        "--datadir",
        type=Path,
        default=f"{pkg_root}/data",
        help="Path to the data directory.",
    )
    parser.add_argument(
        "--outdir", type=Path, default="./out", help="Path to the output directory."
    )
    parser.add_argument(
        "--replace", action="store_true", help="Replace existing output."
    )
    parser.add_argument(
        "--tokenizer",
        type=str,
        default="xml",
        help="Use a custom tokenizer or 'xml' or 'char'.",
    )
    parser.add_argument("--filter-file", type=str, help="Filter file.")
    parser.add_argument("--halt-on-error", action="store_true", help="Halt on error.")
    parser.add_argument(
        "--operation",
        type=str,
        help="Name of the operation to test. Changes the filenames of the comparisons.",
    )
    parser.add_argument(
        "--save-as-test-cases",
        action="store_true",
        help="Save the output of the markup engines as test cases.",
    )

    args = parser.parse_args()
    setup_catalog_env_var()

    if args.tokenizer == "xml" or not args.tokenizer:
        tokenizer: TokenizerProtocol = XMLTokenizer()
    elif args.tokenizer == "char":
        tokenizer = CharacterTokenizer()
    else:
        tokenizer_engine = load_engine(args.tokenizer, "Tokenizer")
        tokenizer = cast(TokenizerProtocol, tokenizer_engine)

    datadir = Path(args.datadir)
    outdir = Path(args.outdir)

    metric_engine_scripts = sorted(glob.glob(args.metric_engines))

    if not metric_engine_scripts:
        raise ArgumentParseError(f"No metric engines found: {args.metric_engines}")

    automarkup_engine_scripts = sorted(glob.glob(args.automarkup_engines))

    if not automarkup_engine_scripts:
        raise ArgumentParseError(
            f"No automarkup engines found: {args.automarkup_engines}"
        )

    if args.filter_file:
        with open(args.filter_file) as f:
            filter_list = f.read().splitlines()
    else:
        filter_list = None

    if outdir.exists():
        print(
            f"Out directory already exists: {outdir}"
            + ("Replacing." if args.replace else "")
        )
        if args.replace:
            shutil.rmtree(outdir)
        else:
            raise ArgumentParseError(
                "Out directory already exists, use --replace to replace."
            )

    outdir.mkdir(parents=True)
    logger = SimpleLogger(outdir / "log.txt")

    config = Config(
        automarkup_engine_scripts,
        metric_engine_scripts,
        datadir,
        outdir,
        tokenizer,
        logger,
        ProfileLogger(),
        filter_list,
        args.operation or "",
        args.halt_on_error,
        args.save_as_test_cases,
    )
    return config


def main():
    try:
        config = parse_args()
    except ArgumentParseError as e:
        print(str(e))
        return 1
    generate_results(config)


if __name__ == "__main__":
    main()
