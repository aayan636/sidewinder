from typing import Protocol

from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from sidewinder.analysis.symbolic.runtime.effect.guarded_effect import GuardedEffect


class Effector(Protocol):
    def __call__(self, *args: SymbolicValue) -> list[GuardedEffect]:
        ...