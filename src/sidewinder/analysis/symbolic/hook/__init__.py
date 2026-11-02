from sidewinder.analysis.symbolic.hook.sidewinder_hook import SidewinderHook, SidewinderHookNames

from sidewinder.analysis.symbolic.hook.control_flow.call import __sidewinder_call__
from sidewinder.analysis.symbolic.hook.control_flow.return_ import __sidewinder_return__
from sidewinder.analysis.symbolic.hook.state_mutator.getattr import __sidewinder_getattr__
from sidewinder.analysis.symbolic.hook.condition_stack.condition_stack import __sidewinder_condition_false__, __sidewinder_condition_true__, __sidewinder_pop_condition__

from typing import Callable

hook_map: dict[SidewinderHookNames, Callable] = {
    SidewinderHookNames.SIDEWINDER_CALL: __sidewinder_call__,
    SidewinderHookNames.SIDEWINDER_RETURN: __sidewinder_return__,
    SidewinderHookNames.SIDEWINDER_GETATTR: __sidewinder_getattr__,
    SidewinderHookNames.SIDEWINDER_CONDITION_TRUE: __sidewinder_condition_true__,
    SidewinderHookNames.SIDEWINDER_CONDITION_FALSE: __sidewinder_condition_false__,
    SidewinderHookNames.SIDEWINDER_POP_CONDITION: __sidewinder_pop_condition__
}

__all__ = ["hook_map", "SidewinderHookNames"]
