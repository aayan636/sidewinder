from typing import Any
from sidewinder.analysis.symbolic.runtime.effect.effect_type import EffectType

class Effect:
    callsite: Any #TODO: remove this any
    type: EffectType

    def __init__(self, callsite: Any, type: EffectType):
        self.callsite = callsite
        self.type = type

    def __str__(self):
        # TODO: When we add callsite, this needs to change
        return str(self.type)