from __future__ import annotations

from analysis.symbolic.runtime.state.effect import Effect
from analysis.symbolic.runtime.values.symbolic_value import SymbolicValue


class GuardedEffect:
    condition: SymbolicValue
    effect: Effect