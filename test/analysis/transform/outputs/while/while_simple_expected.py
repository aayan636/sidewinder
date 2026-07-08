from sidewinder.analysis.symbolic.state import SidewinderState

__sidewinder_cond0 = x
__sidewinder_fixed_point1 = False
while not __sidewinder_fixed_point1:
    __sidewinder_condition_true__(__sidewinder_cond0, __sidewinder_state=__sidewinder_state)
    y1
    __sidewinder_cond0 = __sidewinder_union__(__sidewinder_cond0, x, __sidewinder_state=__sidewinder_state)
    __sidewinder_fixed_point1 = __sidewinder_fixed_point__(__sidewinder_state=__sidewinder_state)
    __sidewinder_pop_condition__(__sidewinder_state=__sidewinder_state)
__sidewinder_condition_false__(__sidewinder_cond0, __sidewinder_state=__sidewinder_state)