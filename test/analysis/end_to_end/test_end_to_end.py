# testDriver.py
import ast
import pytest
from pathlib import Path
from sidewinder.analysis.transform.transformer import SidewinderTransformer  # adjust import path
from sidewinder.analysis.symbolic.runtime.runtime import SidewinderRuntime
from sidewinder.analysis.tools.effect_explorer import EffectExplorer


INPUTS_DIR = Path(__file__).parent / "inputs"
TEMP_DIR = Path(__file__).parent / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def discover_tests() -> list[Path]:
    """
    Discover input/output test pairs.
    Flags:
    - inputs with no matching expected output
    - expected outputs with no matching input
    """
    input_files = set(INPUTS_DIR.glob("**/*.py"))

    # map stem -> path for inputs
    input_map = {f.stem: f for f in input_files}
    return [input_map[stem] for stem in input_map]


def _parse_file(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


test_cases = discover_tests()

@pytest.mark.parametrize(
        "input_file", 
        test_cases, 
        ids=[f"{input_file.parent.stem}::{input_file.stem}" for input_file in test_cases]
)
def test_transformer(input_file: Path) -> None:
    # parse input
    if "if" not in input_file.__str__():
        pytest.skip()
    input_tree = _parse_file(input_file)

    # transform
    transformer = SidewinderTransformer()
    actual_tree = transformer.visit(input_tree)
    ast.fix_missing_locations(actual_tree)

    intermediate_code = ast.unparse(actual_tree)

    with open(TEMP_DIR / input_file.name, "w") as f:
        f.writelines(intermediate_code)

    runtime = SidewinderRuntime()
    captured_effects = runtime.exec_code(intermediate_code, original_code_location=input_file.absolute())

    explorer = EffectExplorer(captured_effects)
    print(captured_effects)