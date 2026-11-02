
from copy import deepcopy
from collections import defaultdict

from sidewinder.analysis.symbolic.runtime.values.symbolic_value import SymbolicValue
from sidewinder.analysis.symbolic.runtime.values.symbolic_condition import SymbolicCondition
from sidewinder.analysis.symbolic.runtime.values.effector import Effector, EffectorOnCallStack
from sidewinder.analysis.symbolic.runtime.effect.guarded_effect import GuardedEffect
from sidewinder.analysis.symbolic.runtime.effect import Effect
from sidewinder.analysis.symbolic.runtime.effect.returns_effect import ReturnsEffect

class SidewinderState:
    stackFrameToPathCondition: dict[EffectorOnCallStack, list[SymbolicCondition]]
    effects: dict[EffectorOnCallStack, list[GuardedEffect]]
    callStack: list[EffectorOnCallStack]

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

    def pushToCallStack(self, effector: Effector):
        newEffectorOnCallStack = EffectorOnCallStack(effector)
        if len(self.callStack) > 0:
            previousEffectorOnCallStack = self.callStack[-1]
            currentPathCondition = self.stackFrameToPathCondition[previousEffectorOnCallStack]
            previousEffectorOnCallStack.link_inner_effect(currentPathCondition, newEffectorOnCallStack)
        self.callStack.append(newEffectorOnCallStack)

    def popFromCallStack(self):
        assert len(self.callStack) > 0
        self.callStack.pop()

    def pushToPathCondition(self, symbolicValue: SymbolicValue, polarity: bool):
        assert len(self.callStack) > 0
        latestCallFrame = self.callStack[-1]
        self.stackFrameToPathCondition[latestCallFrame].append(SymbolicCondition(symbolicValue, polarity))

    def popFromPathCondition(self):
        assert len(self.callStack) > 0
        latestCallFrame = self.callStack[-1]
        # TODO: We should only pop the last condition. otherwise nested ifs will fail
        conditionsBeingPopped = self.stackFrameToPathCondition[latestCallFrame]
        # When we analyse a blob of code, we do not consider the condition stack external to it. 
        # We should add the conditions to the effect when popping the condition from the condition stack.
        # TODO: Should this be done recursively?
        inner_effectors = latestCallFrame.get_inner_effects(conditionsBeingPopped)
        for inner_effector in inner_effectors:
            effects = self.effects[inner_effector]
            for effect in effects:
                effect.condition.extend(conditionsBeingPopped)
        self.stackFrameToPathCondition[latestCallFrame].pop()