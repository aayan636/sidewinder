from sidewinder.analysis.symbolic.runtime.effect.effect_type import EffectType
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from enum import Enum, auto

class OperationType(Enum):
    READ = auto()
    WRITE = auto()
    READ_WRITE = auto()

class ExternalEffect(EffectType):
    operation: OperationType
    resource: SymbolicValue

    def __init__(self, operation: OperationType, resource: SymbolicValue):
        self.operation = operation
        self.resource = resource