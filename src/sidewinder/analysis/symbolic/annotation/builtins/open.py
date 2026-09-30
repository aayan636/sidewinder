from sidewinder.analysis.symbolic.runtime.effect.external_effect import ExternalEffect, OperationType
from sidewinder.analysis.symbolic.runtime.effect.returns_effect import ReturnsEffect
from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.values.heap_object import HeapObject
from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState

def open(file, mode="r", *, _sidewinder_state: SidewinderState):
    if "w" in mode:
        _sidewinder_state.addEffect(Effect(callsite=None, type=ExternalEffect(OperationType.WRITE, file)))
    _sidewinder_state.addEffect(Effect(callsite=None, type=ReturnsEffect(FilePointer(file, mode))))

class FilePointer(HeapObject):
    def __init__(self, name, mode):
        super().__init__()
        self.name = name
        self.mode = mode

    def __enter__(self, *, _sidewinder_state: SidewinderState):
        _sidewinder_state.addEffect(Effect(callsite=None, type=ReturnsEffect(self)))

    def __exit__(self, exc_type, exc_value, traceback, *, _sidewinder_state: SidewinderState):
        # TODO: Exception handling should be here
        pass

    def read(self, size=-1, *, _sidewinder_state: SidewinderState):
        _sidewinder_state.addEffect(Effect(callsite=None, type=ExternalEffect(OperationType.READ, self.name)))
        _sidewinder_state.addEffect(Effect(callsite=None, type=ReturnsEffect(str())))  # TODO: is this the best thing here?

    def write(self, data, *, _sidewinder_state: SidewinderState):
        _sidewinder_state.addEffect(Effect(callsite=None, type=ExternalEffect(OperationType.WRITE, self.name)))
        _sidewinder_state.addEffect(Effect(callsite=None, type=ReturnsEffect(int())))  # TODO: is this the best thing here?
