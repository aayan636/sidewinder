from analysis.symbolic.hook.sidewinder_hook import SidewinderHook, SidewinderHookNames

from typing import Dict


hook_map: Dict[SidewinderHookNames, SidewinderHook] = {}


__all__ = ["hook_map", "SidewinderHookNames"]
