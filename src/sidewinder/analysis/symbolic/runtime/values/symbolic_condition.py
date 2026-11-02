from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue

class SymbolicCondition:
    value: "SymbolicValue"
    polarity: bool

    def __init__(self, value: "SymbolicValue", polarity: bool):
        self.value = value
        self.polarity = polarity

    def __str__(self):
        return f"(Condition is {self.polarity}: {self.value})"