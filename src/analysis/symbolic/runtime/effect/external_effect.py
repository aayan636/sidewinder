from analysis.symbolic.runtime.state.effect.effect_type import EffectType
from analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from enum import Enum, auto

class OperationType(Enum):
    READ = auto()
    WRITE = auto()
    READ_WRITE = auto()

class ExternalEffect(EffectType):
    operation: OperationType
    resource: SymbolicValue