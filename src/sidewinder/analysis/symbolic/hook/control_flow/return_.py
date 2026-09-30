from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
from sidewinder.analysis.symbolic.runtime.values.heap_object import HeapObject
from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.effect.returns_effect import ReturnsEffect

def __sidewinder_return__(object: HeapObject, *, __sidewinder_state: SidewinderState):
    __sidewinder_state.addEffect(Effect(callsite=None, type=ReturnsEffect(object)))