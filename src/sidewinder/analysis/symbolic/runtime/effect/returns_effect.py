from sidewinder.analysis.symbolic.runtime.effect.effect_type import EffectType
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue

class ReturnsEffect(EffectType):
    value: SymbolicValue

    def __init__(self, value: SymbolicValue):
        self.value = value
