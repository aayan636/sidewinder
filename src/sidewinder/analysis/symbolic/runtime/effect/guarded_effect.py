from __future__ import annotations

from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue


class GuardedEffect:
    condition: list[SymbolicValue]
    effect: Effect

    def __init__(self, condition: list[SymbolicValue], effect: Effect):
        self.condition = condition
        self.effect = effect

    def __str__(self):
        return f"(Guarded Effect: (Condition: {self.condition}) (Effect: {self.effect}))"