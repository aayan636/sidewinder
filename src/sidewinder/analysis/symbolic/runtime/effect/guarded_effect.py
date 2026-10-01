from __future__ import annotations

from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue


class GuardedEffect:
    condition: list[SymbolicValue]
    effect: Effect

    def __init__(self, condition: list[SymbolicValue], effect: Effect):
        self.condition = condition
        self.effect = effect