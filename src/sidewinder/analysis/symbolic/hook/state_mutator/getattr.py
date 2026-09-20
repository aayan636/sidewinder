from typing import Any

from sidewinder.analysis.symbolic.runtime.memory.state import SidewinderState
from sidewinder.analysis.symbolic.runtime.values.heap_object import HeapObject
from sidewinder.analysis.symbolic.runtime.values.key import Key

def __sidewinder_getattr__(object: HeapObject, key: Key, *args: list[Any], __sidewinder_state: SidewinderState, **kwargs: dict[str | None, Any]):
    return object.heap_map[key]