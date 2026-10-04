from sidewinder.analysis.symbolic.runtime.effect.effect_type import EffectType, EffectTier
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from sidewinder.analysis.symbolic.runtime.values.effector import Effector

class ReturnsEffect(EffectType):
    value: SymbolicValue

    def __init__(self, value: SymbolicValue):
        super().__init__(EffectTier.VERBOSE)
        self.value = value

    def __str__(self):
        if isinstance(self.value, Effector):
            return f"Returns callable {self.value.__qualname__}"
        else:
            return f"Returns {self.value}"
