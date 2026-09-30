def source(filename, *, __sidewinder_state: SidewinderState):

    def decorator(fn, *, __sidewinder_state: SidewinderState):

        def wrapper(*, __sidewinder_state: SidewinderState):
            __t1 = __sidewinder_call__(open, filename, 'r', __sidewinder_state=__sidewinder_state)
            __mgr0 = __t1
            __sidewinder_attr2 = __sidewinder_getattr__(__mgr0, '__enter__', __sidewinder_state=__sidewinder_state)
            __t3 = __sidewinder_call__(__sidewinder_attr2, __sidewinder_state=__sidewinder_state)
            f = __t3
            __sidewinder_attr4 = __sidewinder_getattr__(f, 'read', __sidewinder_state=__sidewinder_state)
            __t5 = __sidewinder_call__(__sidewinder_attr4, __sidewinder_state=__sidewinder_state)
            __t6 = __sidewinder_call__(fn, __t5, __sidewinder_state=__sidewinder_state)
            __sidewinder_return__(__t6, __sidewinder_state=__sidewinder_state)
            __sidewinder_attr7 = __sidewinder_getattr__(__mgr0, '__exit__', __sidewinder_state=__sidewinder_state)
            __t8 = __sidewinder_call__(__sidewinder_attr7, __sidewinder_state=__sidewinder_state)
            __t8
        __sidewinder_return__(wrapper, __sidewinder_state=__sidewinder_state)
    __sidewinder_return__(decorator, __sidewinder_state=__sidewinder_state)
__t11 = __sidewinder_call__(source, 'users.csv', __sidewinder_state=__sidewinder_state)

def process_users(users, *, __sidewinder_state: SidewinderState):
    __sidewinder_attr9 = __sidewinder_getattr__(users, 'upper', __sidewinder_state=__sidewinder_state)
    __t10 = __sidewinder_call__(__sidewinder_attr9, __sidewinder_state=__sidewinder_state)
    __sidewinder_return__(__t10, __sidewinder_state=__sidewinder_state)
__t12 = __sidewinder_call__(__t11, process_users, __sidewinder_state=__sidewinder_state)
process_users = __t12
__t13 = __sidewinder_call__(process_users, __sidewinder_state=__sidewinder_state)
__t13