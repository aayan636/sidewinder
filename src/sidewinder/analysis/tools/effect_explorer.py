import random
import string

from sidewinder.analysis.symbolic.runtime.values.effector import EffectorOnCallStack
from sidewinder.analysis.symbolic.runtime.effect.guarded_effect import GuardedEffect
from sidewinder.analysis.symbolic.runtime.effect.returns_effect import ReturnsEffect
from sidewinder.analysis.symbolic.runtime.effect.effect_type import EffectTier

# Helpful for tracing the detected effects in dev debug mode
class EffectExplorer:
    def __init__(self, effects: dict[EffectorOnCallStack, list[GuardedEffect]]):
        self.effects = effects
        self.code_to_effect = {''.join(random.choices(string.ascii_lowercase, k=5)): key for key in self.effects.keys()}

    def get_codes(self):
        print({code: func_name.effector.__qualname__ for code, func_name in self.code_to_effect.items()})

    def get_effects(self, code: str, show_verbose: bool = False):
        if code not in self.code_to_effect:
            print(f"No effect found for code {code}")
            return

        print(f"Effects for code {code}")
        self._print_effector(self.code_to_effect[code], show_verbose)


    def _print_effector(self, effector: EffectorOnCallStack, show_verbose: bool, indent: int = 0):
        prefix = "    " * indent

        print(f"\n{prefix}Effector: {effector.effector}")
        print(f"{prefix}{'-' * 30}")
        print(f"{prefix}Effects:")

        for effect in self.effects[effector]:
            if not show_verbose and effect.effect.type.tier == EffectTier.VERBOSE:
                continue
            print(f"{prefix}  {effect}")

        for inner in effector.inner_effector:
            self._print_effector(inner, show_verbose, indent + 1)


        
