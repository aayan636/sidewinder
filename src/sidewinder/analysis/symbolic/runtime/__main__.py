from pathlib import Path

from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
from sidewinder.analysis.symbolic.runtime.runtime import SidewinderRuntime
from sidewinder.analysis.tools.effect_explorer import EffectExplorer

if __name__ == "__main__":
    runtime = SidewinderRuntime()
    path = Path(__file__).parent.parent.parent.parent.parent.parent / "test" / "analysis" / "transform" / "outputs" / "big_one_expected.py"
    with open(path) as f:
        code = "\n".join(f.readlines())
    captured_effects = runtime.exec_code(code, original_code_location=path.absolute())
    explorer = EffectExplorer(captured_effects)
    print(captured_effects)