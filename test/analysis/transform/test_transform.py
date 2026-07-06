# testDriver.py
import ast
import difflib
import pytest
import warnings
from pathlib import Path
from analysis.transform.transformer import SidewinderTransformer  # adjust import path

INPUTS_DIR = Path(__file__).parent / "inputs"
OUTPUTS_DIR = Path(__file__).parent / "outputs"


def discover_tests() -> list[tuple[Path, Path]]:
    """
    Discover input/output test pairs.
    Flags:
    - inputs with no matching expected output
    - expected outputs with no matching input
    """
    input_files = set(INPUTS_DIR.glob("**/*.py"))
    output_files = set(OUTPUTS_DIR.glob("**/*_expected.py"))

    # map stem -> path for inputs
    input_map = {f.stem: f for f in input_files}
    # map stem (without -expected) -> path for outputs
    output_map = {f.stem.removesuffix("_expected"): f for f in output_files}

    # flag unmatched inputs
    for stem, path in input_map.items():
        if stem not in output_map:
            warnings.warn(f"Input file {path.name} has no matching expected output — skipping")

    # flag unmatched outputs  
    for stem, path in output_map.items():
        if stem not in input_map:
            warnings.warn(f"Expected output {path.name} has no matching input — skipping")

    # return matched pairs only
    return [
        (input_map[stem], output_map[stem])
        for stem in input_map
        if stem in output_map
    ]


def _parse_file(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


def _diff(expected: ast.AST, actual: ast.AST) -> str:
    expected_src = ast.unparse(expected)
    actual_src = ast.unparse(actual)
    diff = difflib.unified_diff(
        expected_src.splitlines(keepends=True),
        actual_src.splitlines(keepends=True),
        fromfile="expected",
        tofile="actual",
    )
    return "".join(diff)

test_cases = discover_tests()

@pytest.mark.parametrize(
        "input_file,expected_file", 
        test_cases, 
        ids=[f"{input_file.parent.stem}::{input_file.stem}" for input_file, _ in test_cases]
)
def test_transformer(input_file: Path, expected_file: Path) -> None:
    # parse input
    input_tree = _parse_file(input_file)

    # transform
    transformer = SidewinderTransformer()
    actual_tree = transformer.visit(input_tree)
    ast.fix_missing_locations(actual_tree)

    # parse expected output
    expected_tree = _parse_file(expected_file)

    # compare structurally
    if ast.dump(expected_tree) != ast.dump(actual_tree):
        diff = _diff(expected_tree, actual_tree)
        pytest.fail(
            f"\nTransformer output does not match expected for {input_file.name}\n"
            f"\n--- DIFF ---\n{diff}\n"
            f"\n--- EXPECTED ---\n{ast.unparse(expected_tree)}\n"
            f"\n--- ACTUAL ---\n{ast.unparse(actual_tree)}\n"
        )