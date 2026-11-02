from __future__ import annotations

from typing import Any, Protocol, runtime_checkable, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
    from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
    from sidewinder.analysis.symbolic.runtime.values.symbolic_condition import SymbolicCondition

@runtime_checkable
class Effector(Protocol):
    def __call__(self, *args: list[SymbolicValue], _sidewinder_state: SidewinderState, **kwargs: dict[str, SymbolicValue]) -> Any:
            ...

class EffectorOnCallStack:
    effector: Effector
    inner_effector: dict[tuple["SymbolicCondition", ...], list["EffectorOnCallStack"]]

    def __init__(self, effector: Effector):
        self.effector = effector
        self.inner_effector = defaultdict(list)

    def __hash__(self) -> int:
        return self.effector.__hash__() + id(self.inner_effector).__hash__()

    def link_inner_effect(self, pathCondition: list[SymbolicCondition], inner_effector_on_call_stack: EffectorOnCallStack):
        self.inner_effector[tuple(pathCondition)].append(inner_effector_on_call_stack)

    def get_inner_effects(self, pathCondition: list[SymbolicCondition]) -> list["EffectorOnCallStack"]:
        return self.inner_effector[tuple(pathCondition)]