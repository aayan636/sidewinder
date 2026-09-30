from __future__ import annotations

from typing import Any, Protocol, runtime_checkable, TYPE_CHECKING


if TYPE_CHECKING:
    from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
    from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState

@runtime_checkable
class Effector(Protocol):
    def __call__(self, *args: list[SymbolicValue], __sidewinder_state: SidewinderState, **kwargs: dict[str, SymbolicValue]) -> Any:
            ...