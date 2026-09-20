from __future__ import annotations
from typing import cast
from sidewinder.analysis.symbolic.runtime.values.key import Key
from sidewinder.analysis.symbolic.runtime.values.symbolic_type import SymbolicType
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue


class HeapObject:
    id: int
    heap_map: dict[Key, SymbolicValue]
    type: SymbolicType

    def __init_subclass__(cls):
        super().__init_subclass__()

        cls._heap_map = {
            cast(Key, name): cast(SymbolicValue, value)
            for name, value in cls.__dict__.items()
        }

    def __init__(self):
        self.heap_map = self._heap_map