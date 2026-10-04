from __future__ import annotations

from typing import Any, Protocol, runtime_checkable, TYPE_CHECKING


if TYPE_CHECKING:
    from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
    from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState

@runtime_checkable
class Effector(Protocol):
    def __call__(self, *args: list[SymbolicValue], _sidewinder_state: SidewinderState, **kwargs: dict[str, SymbolicValue]) -> Any:
            ...

class EffectorOnCallStack:
    effector: Effector
    inner_effector: list["EffectorOnCallStack"]

    def __init__(self, effector: Effector):
        self.effector = effector
        self.inner_effector = []

    def link_inner_effect(self, inner_effector_on_call_stack: EffectorOnCallStack):
        self.inner_effector.append(inner_effector_on_call_stack)