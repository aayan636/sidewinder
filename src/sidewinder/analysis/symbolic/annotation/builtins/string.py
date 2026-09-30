from sidewinder.analysis.symbolic.runtime.values.heap_object import HeapObject
from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.effect.returns_effect import ReturnsEffect

class SymbolicString(HeapObject):
    def __init__(self, base_string: str):
        super().__init__()
        self.base_str = base_string

    def upper(self, _sidewinder_state: SidewinderState):
        _sidewinder_state.addEffect(Effect(callsite=None, type=ReturnsEffect(self)))