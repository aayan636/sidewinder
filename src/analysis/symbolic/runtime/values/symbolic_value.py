from __future__ import annotations

from typing import TypeAlias

from analysis.symbolic.runtime.values.effector import Effector
from analysis.symbolic.runtime.values.heap_object import HeapObject
from analysis.symbolic.runtime.values.primitive import Primitive


SymbolicValue: TypeAlias = (
    Primitive
    | HeapObject
    | Effector
)