from enum import Enum, auto

class EffectTier(Enum):
    ACTIONABLE = auto()
    VERBOSE= auto()


class EffectType:
    tier: EffectTier