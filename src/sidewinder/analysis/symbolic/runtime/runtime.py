from typing import Callable
from pathlib import Path

from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState

class SidewinderRuntime:

    def __init__(self):
        from sidewinder.analysis.symbolic.hook import hook_map
        from sidewinder.analysis.symbolic.annotation.builtins.open import open
        self.sidewinder_state = SidewinderState()
        self.hooks = {f"__{hook_name.name.lower()}__": hook for (hook_name, hook) in hook_map.items()}
        self.annotations = {"open": open}

    def exec_code(self, transformed_code: str, original_code_location: Path):
        global_variables: dict[str, str | Callable | SidewinderState | dict] = {
            '__name__': f'__sidewinder_{original_code_location}',
            '__builtins__': {},
            'SidewinderState': SidewinderState
        }
        global_variables.update(self.hooks)
        global_variables.update(self.annotations)
        global_variables["_sidewinder_state"] = self.sidewinder_state

        exec(transformed_code, global_variables)

        new_state: SidewinderState = global_variables["_sidewinder_state"]
        return new_state.effects