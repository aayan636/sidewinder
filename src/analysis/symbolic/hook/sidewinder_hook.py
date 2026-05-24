from enum import Enum, auto
from typing import Any, Protocol

from analysis.symbolic.runtime.memory.state import SidewinderState


class SidewinderHookCallable(Protocol):
    def __call__(self, *args: Any, __sidewinder_state__: SidewinderState, **kwargs: Any) -> Any:
        ...
    

class SidewinderHookNames(Enum):
    # Symbolic Value
    SIDEWINDER_FETCH_SYMBOL = auto()
    SIDEWINDER_NEW = auto()

    # Condition Stack
    SIDEWINDER_CONDITION_TRUE = auto()
    SIDEWINDER_CONDITION_FALSE = auto()
    SIDEWINDER_POP_CONDITION = auto()

    # Control Flow
    SIDEWINDER_FIXED_POINT = auto()
    SIDEWINDER_UNION = auto()
    SIDEWINDER_RETURN = auto()
    SIDEWINDER_CONTINUE = auto()
    SIDEWINDER_BREAK = auto()
    SIDEWINDER_RAISE = auto()
    SIDEWINDER_YIELD = auto()
    SIDEWINDER_YIELD_FROM = auto()
    SIDEWINDER_CALL = auto()

    # Exception Semantics
    SIDEWINDER_EXCEPTION_CONDITION_AND_OBJECT = auto()
    SIDEWINDER_THROWN = auto()
    SIDEWINDER_NOT_THROWN = auto()

    # Heap Read/Write (explicit memory operations)
    SIDEWINDER_GETITEM = auto()
    SIDEWINDER_SETITEM = auto()
    SIDEWINDER_DELITEM = auto()

    # State Mutators
    SIDEWINDER_GETATTR = auto()
    SIDEWINDER_SETATTR = auto()
    SIDEWINDER_WRITE_GLOBAL = auto()
    SIDEWINDER_WRITE_HEAP = auto()
    SIDEWINDER_WRITE_NONLOCAL = auto()

    # Operators
    SIDEWINDER_BOOL = auto()
    SIDEWINDER_UNARY_OP = auto()
    SIDEWINDER_BINARY_OP = auto()
    SIDEWINDER_ASSERT = auto()


class SidewinderHook:
    _name: str
    _method: SidewinderHookCallable

    def __init__(self, name: SidewinderHookNames, method: SidewinderHookCallable):
        self._name = f"__{name.name.lower()}__"
        self._method = method

    @property
    def name(self) -> str:
        return self._name

    @property
    def method(self) -> SidewinderHookCallable:
        return self._method