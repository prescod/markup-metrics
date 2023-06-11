import importlib.util
import glob
import os
from pathlib import Path
import argparse
from xml.etree.ElementTree import XMLParser, parse
from xml.sax import SAXParseException
from metrics.types import MetricInput
from typing import Callable, Optional, Tuple, Type
import statistics
from markup_metrics.tokenize_xml import tokenize_xml


def load_class(script: str, class_name: str):
    spec = importlib.util.spec_from_file_location("module", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


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
) -> Tuple[float, bool, Optional[Path]]:
    xml_path = txt_path.with_suffix(".xml")
    reference_text = parse_reference_text(xml_path)
    if reference_text is None:
        return 0, False, None

    with txt_path.open("r") as file:
        input_text = file.read()

    output_text = automarkup.automarkup(input_text, prompt)
    relative_path = txt_path.relative_to(txt_path.parent.parent)
    output_file_path = (
        engine_outdir / relative_path.parent / txt_path.stem / (txt_path.stem + ".xml")
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
    )
    metric_output = output_file_path.with_suffix(f".{metric_engine.name}.txt")
    if metric_output.exists():
        metric_output.unlink()

    score = metric_engine.calculate(validator_input, metric_output)

    return score, True, output_file_path


def process_schema_directory(
    schema_dir: Path,
    automarkup,
    metric_engine,
    tokenizer: Callable,
    engine_outdir: Path,
) -> Tuple[float, int, int]:
    prompt = parse_prompt(schema_dir)
    score_sum = 0
    file_count = 0
    error_count = 0

    print(f"     {schema_dir.stem}")

    for txt_path in schema_dir.glob("*.txt"):
        if txt_path.stem != "prompt":
            score, success, output_file = process_file(
                txt_path, automarkup, metric_engine, prompt, tokenizer, engine_outdir
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


def load_engine(engine_script: str, class_name: str) -> Optional[Type]:
    engine_class = load_class(engine_script, class_name)
    engine_name = Path(engine_script).stem
    engine_class.name = engine_name
    try:
        engine_instance = engine_class()
    except AssertionError as e:
        print(f"Cannot instantiate {class_name.lower()} engine: ", e)
        print(f"Skipping {class_name.lower()} engine: ", engine_class.name)
        return None
    return engine_instance


def process_automarkup_metric_combination(
    markup_engine: Type,
    metric_engine: Type,
    datadir: Path,
    outdir: Path,
    tokenizer: Callable,
):

    engine_outdir = outdir / markup_engine.name

    schema_scores = []

    for schema_dir in datadir.iterdir():
        if schema_dir.is_dir():
            schema_name = schema_dir.stem

            score_sum, file_count, _ = process_schema_directory(
                schema_dir, markup_engine, metric_engine, tokenizer, engine_outdir
            )

            if file_count > 0:
                average_score = score_sum / file_count
                schema_scores.append(average_score)
                print(
                    f"     Average {markup_engine.name} / {metric_engine.name} / {schema_name}: {average_score:.2f}{metric_engine.unit}"
                )

    if schema_scores:
        overall_average = statistics.mean(schema_scores)
        print(
            f"     Average {markup_engine.name} / {metric_engine.name}: {overall_average:.2f}{metric_engine.unit}\n"
        )


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

    if os.environ.get("XML_CATALOG_FILES"):
        print("XML_CATALOG_FILES set, ignoring and overriding it.")
    catalog_files = Path(__file__).parent.parent / "schemas/catalog.xml"
    os.environ["XML_CATALOG_FILES"] = str(catalog_files)
    assert catalog_files.exists()

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

    markup_engines = [load_engine(automarkup_engine_script, "AutoMarkup") for automarkup_engine_script in automarkup_engine_scripts]
    markup_engines = [markup_engine for markup_engine in markup_engines if markup_engine is not None]

    metric_engines = [load_engine(metric_engine_script, "MetricEngine") for metric_engine_script in metric_engine_scripts]
    metric_engines = [metric_engine for metric_engine in metric_engines if metric_engine is not None]

    for markup_engine in markup_engines:
        for metric_engine in metric_engines:
            print(
                f"Processing {markup_engine.name} with {metric_engine.name}"
            )
            process_automarkup_metric_combination(
                markup_engine,
                metric_engine,
                datadir,
                outdir,
                tokenizer,
            )


if __name__ == "__main__":
    main()