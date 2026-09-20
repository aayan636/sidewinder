
from copy import deepcopy
from collections import defaultdict

from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from sidewinder.analysis.symbolic.runtime.values.effector import Effector
from sidewinder.analysis.symbolic.runtime.effect.guarded_effect import GuardedEffect
from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.effect.returns_effect import ReturnsEffect

class SidewinderState:
    stackFrameToPathCondition: dict[Effector, list[SymbolicValue]]
    effects: dict[Effector, list[GuardedEffect]]
    callStack: list[Effector]

    def __init__(self):
        self.stackFrameToPathCondition = defaultdict(list)
        self.effects = defaultdict(list)
        self.callStack = []

    def addEffect(self, newEffect: Effect):
        assert len(self.callStack) > 0
        latestCallFrame = self.callStack[-1]
        latestPathCondition = deepcopy(self.stackFrameToPathCondition[latestCallFrame])
        guardedEffect = GuardedEffect(effect=newEffect, condition=latestPathCondition)
        self.effects[latestCallFrame].append(guardedEffect)

    def getReturnEffect(self):
        assert len(self.callStack) > 0
        latestCallFrame = self.callStack[-1]
        latestEffects = self.effects[latestCallFrame]
        return [effect for effect in latestEffects if isinstance(effect.effect.type, ReturnsEffect)]