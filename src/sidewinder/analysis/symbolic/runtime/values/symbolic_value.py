from __future__ import annotations

from typing import TypeAlias

from sidewinder.analysis.symbolic.runtime.values.effector import Effector
from sidewinder.analysis.symbolic.runtime.values.heap_object import HeapObject
from sidewinder.analysis.symbolic.runtime.values.primitive import Primitive


SymbolicValue: TypeAlias = (
    Primitive
    | HeapObject
    | Effector
)