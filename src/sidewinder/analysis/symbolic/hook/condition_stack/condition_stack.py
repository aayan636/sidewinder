from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState

def __sidewinder_condition_true__(conditionSymbolicValue: SymbolicValue, _sidewinder_state: SidewinderState, **kwargs: dict[str, SymbolicValue]):
    _sidewinder_state.pushToPathCondition(conditionSymbolicValue, True)

def __sidewinder_condition_false__(conditionSymbolicValue: SymbolicValue, _sidewinder_state: SidewinderState, **kwargs: dict[str, SymbolicValue]):
    _sidewinder_state.pushToPathCondition(conditionSymbolicValue, False)

def __sidewinder_pop_condition__( _sidewinder_state: SidewinderState, **kwargs: dict[str, SymbolicValue]):
    _sidewinder_state.popFromPathCondition()