from typing import Any

from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
from sidewinder.analysis.symbolic.runtime.values.effector import Effector

def __sidewinder_call__(effector: Effector, *args: list[Any], __sidewinder_state: SidewinderState, **kwargs: dict[str | None, Any]):
    pass