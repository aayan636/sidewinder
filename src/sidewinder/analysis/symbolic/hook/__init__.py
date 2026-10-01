from sidewinder.analysis.symbolic.hook.sidewinder_hook import SidewinderHook, SidewinderHookNames

from sidewinder.analysis.symbolic.hook.control_flow.call import __sidewinder_call__
from sidewinder.analysis.symbolic.hook.control_flow.return_ import __sidewinder_return__
from sidewinder.analysis.symbolic.hook.state_mutator.getattr import __sidewinder_getattr__

from typing import Callable

hook_map: dict[SidewinderHookNames, Callable] = {
    SidewinderHookNames.SIDEWINDER_CALL: __sidewinder_call__,
    SidewinderHookNames.SIDEWINDER_RETURN: __sidewinder_return__,
    SidewinderHookNames.SIDEWINDER_GETATTR: __sidewinder_getattr__
}

__all__ = ["hook_map", "SidewinderHookNames"]
