from sidewinder.analysis.symbolic.runtime.effect.effect_type import EffectType
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue

class ThrowsEffect(EffectType):
    throws: SymbolicValue

    def __init__(self, throws: SymbolicValue):
        super().__init__()
        self.throws = throws

    def __str__(self):
        return f"Throws {self.throws}"