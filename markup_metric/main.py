import importlib.util
import glob
import os
from pathlib import Path
import argparse
from xml.etree.ElementTree import XMLParser, parse
from xml.sax import SAXParseException
from metrics.types import MetricInput
from typing import Callable, Optional, Tuple
import statistics
from markup_metric.tokenize_xml import tokenize_xml


def load_module(script: str, class_name: str):
    spec = importlib.util.spec_from_file_location("module", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def parse_prompt(schema_dir: Path) -> str:
    prompt_path = schema_dir / "prompt.txt"
    with prompt_path.open("r") as file:
        return file.read()


def parse_reference_text(xml_path: Path) -> str:
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
    output_file_path = engine_outdir /  / relative_path.with_suffix(".xml")
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
                print(f"            {txt_path} ({output_file}): {score}")
            else:
                error_count += 1

    return score_sum, file_count, error_count


def process_automarkup_metric_combination(
    automarkup_engine_script: str,
    metric_engine_script: str,
    datadir: Path,
    outdir: Path,
    tokenizer: Callable,
):
    automarkup = load_module(automarkup_engine_script, "AutoMarkup")
    engine_name = Path(automarkup_engine_script).stem
    automarkup.name = engine_name
    metric_engine = load_module(metric_engine_script, "MetricEngine")
    metric_name = Path(metric_engine_script).stem
    metric_engine.name = metric_name
    engine_outdir = outdir / engine_name

    schema_scores = []

    for schema_dir in datadir.iterdir():
        if schema_dir.is_dir():
            schema_name = schema_dir.stem
            score_sum, file_count, _ = process_schema_directory(
                schema_dir, automarkup(), metric_engine(), tokenizer, engine_outdir
            )

            if file_count > 0:
                average_score = score_sum / file_count
                schema_scores.append(average_score)
                print(
                    f"     Average {engine_name} / {metric_name} / {schema_name}: {average_score}"
                )

    if schema_scores:
        overall_average = statistics.mean(schema_scores)
        print(f"     Average {engine_name} / {metric_name}: {overall_average}\n")


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

    from lxml import etree

    # xml_file_path = '/Users/paul/code/markup-metric/out/gpt3.5_turbo_automarkup/dita/test1.xml'
    # parser = etree.XMLParser(dtd_validation=True, load_dtd=True, resolve_entities=True)
    # tree = etree.parse(xml_file_path, parser=parser)
    # assert not len(parser.error_log)

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

    for automarkup_engine_script in automarkup_engine_scripts:
        for metric_engine_script in metric_engine_scripts:
            print(
                f"Processing {Path(automarkup_engine_script).stem} with {Path(metric_engine_script).stem}"
            )
            process_automarkup_metric_combination(
                automarkup_engine_script,
                metric_engine_script,
                datadir,
                outdir,
                tokenizer,
            )


if __name__ == "__main__":
    main()
