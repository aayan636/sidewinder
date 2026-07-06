from __future__ import annotations

from sidewinder.analysis.symbolic.runtime.values.key import Key
from sidewinder.analysis.symbolic.runtime.values.symbolic_type import SymbolicType
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue


class HeapObject:
    id: int
    heap_map: dict[Key, SymbolicValue]
    type: SymbolicType