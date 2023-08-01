import glob
from pathlib import Path
import argparse
import shutil
from xml.etree.ElementTree import XMLParser, parse
from xml.sax import SAXParseException
from markup_engines.types import MarkupEngine
from markup_metrics.profile_logger import ProfileLogger
from markup_metrics.test_metrics import MetricEngine
from metrics.types import MetricInput
from typing import Any, Callable, Generator, List, NamedTuple, Optional, Protocol, Tuple, Type
import statistics
from markup_metrics.tokenize_xml import tokenize_xml
from prettytable import PrettyTable

from .utils import load_engine, setup_catalog_env_var


def parse_prompt(schema_dir: Path) -> str:
    prompt_path = schema_dir / "prompt.txt"
    with prompt_path.open("r") as file:
        return file.read()


def parse_reference_text(xml_path: Path) -> Optional[str]:
    try:
        with xml_path.open("r") as file:
            reference_text = file.read()
            tokenize_xml(reference_text)
            return reference_text
    except SAXParseException:
        print(f"Error: XML parsing failed for {xml_path}")
        return None



def process_file(
    txt_path: Path,
    automarkup,
    metric_engine,
    prompt: str,
    tokenizer: Callable,
    engine_outdir: Path,
    prof_log: ProfileLogger,
) -> Tuple[float, bool, Optional[Path]]:
    xml_paths = list(txt_path.parent.glob(f"{txt_path.stem}.xml")) + list(txt_path.parent.glob(f"{txt_path.stem}.*.xml"))
    results = []
    for xml_path in xml_paths:
        try:
            result = compare_with_reference(xml_path, txt_path, automarkup, metric_engine, prompt, tokenizer, engine_outdir, prof_log)
        except Exception as e:
            print(f"            Error: {e}")
            result = 0, False, None
        results.append(result)
    return max(results)

        
def compare_with_reference(    
    xml_path: Path, 
    txt_path: Path,
    automarkup,
    metric_engine,
    prompt: str,
    tokenizer: Callable,
    engine_outdir: Path,
    prof_log: ProfileLogger):
    reference_text = parse_reference_text(xml_path)
    if reference_text is None:
        return 0, False, None

    with txt_path.open("r") as file:
        input_text = file.read()

    with prof_log.log_time(f"{metric_engine.name} for: {txt_path}"):
        output_text = automarkup.automarkup(input_text, prompt)
    relative_path = txt_path.relative_to(txt_path.parent.parent)
    output_file_path = (
        engine_outdir / relative_path.parent / txt_path.stem / (xml_path.stem + ".xml")
    )
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with output_file_path.open("w") as output_file:
        output_file.write(output_text)

    try:
        tokenizer(output_text)
    except SAXParseException as e:
        print(
            f"            Error: XML parsing failed for output, saved to {output_file_path} : {e}"
        )
        return 0, False, None

    validator_input = MetricInput(
        output_text,
        reference_text,
        tokenizer(output_text),
        tokenizer(reference_text),
        profile_logger=prof_log
    )
    metric_output = Path(f"{output_file_path}__{metric_engine.name}")
    if metric_output.exists():
        shutil.rmtree(metric_output)
        
    metric_output.mkdir(parents=True, exist_ok=True)
    with prof_log.log_time(f"{metric_engine.name} for : {txt_path}"):
        score = metric_engine.calculate(validator_input, metric_output)

    return score, True, output_file_path


def process_schema_directory(
    schema_dir: Path,
    automarkup: MarkupEngine,
    metric_engine: MetricEngine,
    tokenizer: Callable,
    engine_outdir: Path,
    prof_log: ProfileLogger,
) -> Tuple[float, int, int]:
    prompt = parse_prompt(schema_dir)
    score_sum = 0
    file_count = 0
    error_count = 0

    print(f"     {schema_dir.stem}")

    for txt_path in schema_dir.glob("*.txt"):
        if txt_path.stem != "prompt":
            score, success, output_file = process_file(
                txt_path, automarkup, metric_engine, prompt, tokenizer, engine_outdir, prof_log
            )
            if success:
                file_count += 1
                score_sum += score
                print(
                    f"            {txt_path} ({output_file}): {score:.2f}{metric_engine.unit}"
                )
            else:
                error_count += 1

    return score_sum, file_count, error_count



# Protocol for engines
class Engine(Protocol):
    name: str

# Type alias for tokenizer
Tokenizer = Callable[..., Any]

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
        markup_engine: MarkupEngine,
        metric_engine: MetricEngine,
        datadir: Path,
        outdir: Path,
        tokenizer: Tokenizer,
        prof_log: ProfileLogger
) -> ProcessingResult:

    engine_outdir = outdir / markup_engine.name

    schema_scores = []

    for schema_dir in datadir.iterdir():
        if schema_dir.is_dir():
            schema_name = schema_dir.stem

            score_sum, file_count, _ = process_schema_directory(
                schema_dir, markup_engine, metric_engine, tokenizer, engine_outdir, prof_log
            )

            if file_count > 0:
                average_score = score_sum / file_count
                schema_scores.append(SchemaScore(schema_name, average_score))

    return ProcessingResult(markup_engine.name, metric_engine.name, schema_scores)


def output_results(automarkup_engine_scripts, metric_engine_scripts, datadir, outdir, tokenizer):
    markup_engines = [load_engine(automarkup_engine_script, "AutoMarkup") for automarkup_engine_script in automarkup_engine_scripts]
    markup_engines = [markup_engine for markup_engine in markup_engines if markup_engine is not None]

    metric_engines = [load_engine(metric_engine_script, "MetricEngine") for metric_engine_script in metric_engine_scripts]
    metric_engines = [metric_engine for metric_engine in metric_engines if metric_engine is not None]

    table_data = []
    times = ProfileLogger()

    for markup_engine in markup_engines:
        for metric_engine in metric_engines:
            print(f"Processing {markup_engine.name} with {metric_engine.name}")

            result = process_automarkup_metric_combination(
                markup_engine,
                metric_engine,
                datadir,
                outdir,
                tokenizer,
                times
            )

            for schema_score in result.schema_scores:
                table_data.append({
                    "Markup Engine": result.markup_engine_name,
                    "Metric Engine": result.metric_engine_name,
                    "Schema Name": schema_score.schema_name,
                    "Average Score": f"{schema_score.average_score:.2f}{metric_engine.unit}"
                })

            if result.schema_scores:
                overall_average = statistics.mean(score.average_score for score in result.schema_scores)
                table_data.append({
                    "Markup Engine": result.markup_engine_name,
                    "Metric Engine": result.metric_engine_name,
                    "Schema Name": "Overall Average",
                    "Average Score": f"{overall_average:.2f}{metric_engine.unit}"
                })

    # Output the data in table format
    if table_data:
        table = PrettyTable()
        table.field_names = ["Markup Engine", "Metric Engine", "Schema Name", "Average Score"]
        for row in table_data:
            table.add_row([row["Markup Engine"], row["Metric Engine"], row["Schema Name"], row["Average Score"]])
        print(table)

    log_file_path = outdir / 'time_logs.txt'
    with log_file_path.open('w') as log_file:
        log_file.write('Context\tTime (s)\tCalls\n')
        for log in times.times:
            log_file.write(f"{log.name}\t{log.time:.6f}\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate markup script.")
    parser.add_argument(
        "--automarkup-engines",
        type=str,
        default="markup_engines/*_automarkup.py",
        help="Glob pattern for the scripts containing the AutoMarkup classes.",
    )
    parser.add_argument(
        "--metric-engines",
        type=str,
        default="metrics/*_metric.py",
        help="Glob pattern for the scripts containing the MetricEngine classes.",
    )
    parser.add_argument(
        "--datadir", type=str, default="./data", help="Path to the data directory."
    )
    parser.add_argument(
        "--outdir", type=str, default="./out", help="Path to the output directory."
    )
    parser.add_argument(
        "--char-tokenizer", action="store_true", help="Use character tokenizer."
    )

    args = parser.parse_args()
    setup_catalog_env_var()

    tokenizer = tokenize_xml if not args.char_tokenizer else list
    datadir = Path(args.datadir)
    outdir = Path(args.outdir)

    metric_engine_scripts = glob.glob(args.metric_engines)

    if not metric_engine_scripts:
        print("No metric engines found.")
        return

    automarkup_engine_scripts = glob.glob(args.automarkup_engines)

    if not automarkup_engine_scripts:
        print("No automarkup engines found.")
        return
    
    output_results(automarkup_engine_scripts, metric_engine_scripts, datadir, outdir, tokenizer)



if __name__ == "__main__":
    main()
