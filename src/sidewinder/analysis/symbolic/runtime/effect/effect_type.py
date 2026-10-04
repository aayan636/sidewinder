from enum import Enum, auto

class EffectTier(Enum):
    ACTIONABLE = auto()
    VERBOSE = auto()


class EffectType:
    tier: EffectTier

    def __init__(self, tier: EffectTier = EffectTier.ACTIONABLE):
        self.tier = tier