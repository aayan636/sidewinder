from typing import Any

from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
from sidewinder.analysis.symbolic.runtime.values.heap_object import HeapObject
from sidewinder.analysis.symbolic.runtime.values.key import Key
from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue

def __sidewinder_getattr__(object: HeapObject, key: Key, *args: list[Any], __sidewinder_state: SidewinderState, **kwargs: dict[str | None, Any]) -> SymbolicValue:
    value = object.heap_map[key]
    
    if hasattr(value, "__get__"):
        return value.__get__(object, type(object))
    
    return value