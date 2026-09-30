from typing import Any

from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from sidewinder.analysis.symbolic.runtime.effect.guarded_effect import GuardedEffect
from sidewinder.analysis.symbolic.runtime.values.effector import Effector
from sidewinder.analysis.symbolic.runtime.effect.returns_effect import ReturnsEffect

def __sidewinder_call__(*effectorAndArgs: list[SymbolicValue], __sidewinder_state: SidewinderState, **kwargs: dict[str, SymbolicValue]) -> SymbolicValue:
    assert len(effectorAndArgs) > 0, "At least one symbolic value must be provided to __sidewinder_call__"
    effector = effectorAndArgs[0]
    args = effectorAndArgs[1:]
    assert isinstance(effector, Effector), "First value provided to __sidewinder_call__ must be Effector"
    __sidewinder_state.pushToCallStack(effector)
    effector.__call__(*args, __sidewinder_state=__sidewinder_state, **kwargs)
    R = __sidewinder_state.getReturnEffect()
    __sidewinder_state.popFromCallStack()
    if len(R) > 1:
        raise NotImplementedError("Only One return effect is supported for now")
    elif len(R) == 0:
        raise NotImplementedError("Expected something to be thrown")
    else:
        if R[0].condition:
            raise NotImplementedError("GuardedEffect not implemented yet")
        else:
            assert isinstance(R[0].effect.type, ReturnsEffect), "This should have been a ReturnsEffect"
            return R[0].effect.type.value
