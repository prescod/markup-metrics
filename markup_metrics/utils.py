import importlib.util
import os
from pathlib import Path
from typing import Optional, Type


def load_class(script: str, class_name: str):
    spec = importlib.util.spec_from_file_location("module", script)
    assert spec and spec.loader, f"Cannot load {script}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


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


def setup_catalog_env_var():
    if os.environ.get("XML_CATALOG_FILES"):
        print("XML_CATALOG_FILES set, ignoring and overriding it.")
    catalog_files = Path(__file__).parent.parent / "schemas/catalog.xml"
    assert catalog_files.exists()
    os.environ["XML_CATALOG_FILES"] = str(catalog_files)
