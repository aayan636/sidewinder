from __future__ import annotations

from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.values.symbolic_condition import SymbolicCondition


class GuardedEffect:
    condition: list[SymbolicCondition]
    effect: Effect

    def __init__(self, condition: list[SymbolicCondition], effect: Effect):
        self.condition = condition
        self.effect = effect

    def __str__(self):
        return f"(Guarded Effect: (Conditions: {", ".join([str(c) for c in self.condition])}) (Effect: {self.effect}))"