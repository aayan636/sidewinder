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
        super().__init__()
        self.operation = operation
        self.resource = resource

    def __str__(self):
        if self.operation == OperationType.READ:
            return f"Reads from {self.resource}"
        elif self.operation == OperationType.WRITE:
            return f"Writes to {self.resource}"
        elif self.operation == OperationType.READ_WRITE:
            return f"Reads and Writes to {self.resource}"
        else:
            raise NotImplementedError(f"Unknown operation: {self.operation}")