from sidewinder.analysis.symbolic.runtime.effect.effect_type import EffectType
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from sidewinder.analysis.symbolic.runtime.values.key import Key

class MutatesEffect(EffectType):
    mutatedHeapObject: SymbolicValue
    mutatedKey: Key

    def __init__(self):
        super().__init__()

    def __str__(self):
        return f"Mutates {self.mutatedHeapObject}'s key {self.mutatedKey}"