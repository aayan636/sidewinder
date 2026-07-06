from typing import Any
from analysis.symbolic.runtime.state.effect.effect_type import EffectType

class Effect:
    callsite: Any #TODO: remove this any
    type: EffectType