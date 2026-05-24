import ast

from analysis.ast.transformer_helpers import SidewinderTransformerHelpers
from analysis.ast.errors import SidewinderIllegalStateError
from analysis.symbolic.hook import SidewinderHookNames

from typing import Any

class SidewinderTryTransformerMixin(SidewinderTransformerHelpers):
    def visit_Try(self, node: ast.Try) -> list[ast.stmt]:
        """
        try:
            body
        except <expr0> as e0:
            handler_0
        except <expr1>:
            handler_1
        except:
            handler_2
        else:
            orelse_body
        finally:
            finally_body

        Becomes:

        # 1. transformed body runs flat — exceptions recorded as may-effects automatically
        <transformed body>

        # 2. each except block — guarded by condition that exception was thrown
        #    already_handled grows with each handler to exclude previously caught exceptions
        __sidewinder_exc_type0__ = <_visit_expr(expr0)>
        __sidewinder_cond0__, e0 = __sidewinder_exception_condition_and_object__(
            __sidewinder_exc_type0__, already_handled=[], __sidewinder_state__)
        __sidewinder_condition_true__(__sidewinder_cond0__, __sidewinder_state__)
        <transformed handler_0>
        __sidewinder_pop_condition__(__sidewinder_state__)

        __sidewinder_exc_type1__ = <_visit_expr(expr1)>
        __sidewinder_cond1__, _ = __sidewinder_exception_condition_and_object__(
            __sidewinder_exc_type1__, already_handled=[__sidewinder_cond0__], __sidewinder_state__)
        __sidewinder_condition_true__(__sidewinder_cond1__, __sidewinder_state__)
        <transformed handler_1>
        __sidewinder_pop_condition__(__sidewinder_state__)

        # bare except — None means catch everything not caught above
        __sidewinder_cond2__, _ = __sidewinder_exception_condition_and_object__(
            None, already_handled=[__sidewinder_cond0__, __sidewinder_cond1__], __sidewinder_state__)
        __sidewinder_condition_true__(__sidewinder_cond2__, __sidewinder_state__)
        <transformed handler_2>
        __sidewinder_pop_condition__(__sidewinder_state__)

        # 3. else block — negation of ALL exception conditions
        __sidewinder_condition_false__(__sidewinder_cond0__, __sidewinder_state__)
        __sidewinder_condition_false__(__sidewinder_cond1__, __sidewinder_state__)
        __sidewinder_condition_false__(__sidewinder_cond2__, __sidewinder_state__)
        <transformed orelse_body>
        __sidewinder_pop_condition__(__sidewinder_state__)
        __sidewinder_pop_condition__(__sidewinder_state__)
        __sidewinder_pop_condition__(__sidewinder_state__)

        # 4. finally — ambient context, no push/pop
        <transformed finally_body>
        """

        result: list[ast.stmt] = []

        # --- 1. Transform try body ---
        result.extend(self._visit_list_of_stmts(node.body))

        # Track condition temps and exc type temps for already_handled
        exception_cond_temps: list[str] = []

        # --- 2. Transform each except handler ---
        for handler in node.handlers:
            exc_type = handler.type
            exc_name = handler.name

            # Evaluate exception type expression symbolically
            if exc_type is not None:
                exc_type_temp = self._fresh_temp("__sidewinder_exc_type")
                result.append(ast.Assign(
                    targets=[ast.Name(id=exc_type_temp, ctx=ast.Store())],
                    value=self._visit_expr(exc_type),
                    lineno=0, col_offset=0,
                ))
                exc_type_arg = ast.Name(id=exc_type_temp, ctx=ast.Load())
            else:
                exc_type_arg = ast.Constant(value=None)

            # Get condition and exception object
            # already_handled = all condition temps collected so far
            cond_temp = self._fresh_temp("__sidewinder_cond")
            discard_temp = self._fresh_temp("__sidewinder_discard")

            result.append(ast.Assign(
                targets=[ast.Tuple(
                    elts=[
                        ast.Name(id=cond_temp, ctx=ast.Store()),
                        ast.Name(id=exc_name if exc_name else discard_temp, ctx=ast.Store()),
                    ],
                    ctx=ast.Store()
                )],
                value=self._emit_hook_call(
                    SidewinderHookNames.SIDEWINDER_EXCEPTION_CONDITION_AND_OBJECT,
                    exc_type_arg,
                    extra_kwargs={
                        "already_handled": ast.List(
                            elts=[ast.Name(id=c, ctx=ast.Load()) for c in exception_cond_temps],
                            ctx=ast.Load()
                        )
                    }
                ),
                lineno=0, col_offset=0,
            ))

            # Push exception condition
            result.append(ast.Expr(
                value=self._emit_hook_call(
                    SidewinderHookNames.SIDEWINDER_CONDITION_TRUE,
                    ast.Name(id=cond_temp, ctx=ast.Load())
                ),
                lineno=0, col_offset=0,
            ))

            # Transform handler body
            result.extend(self._visit_list_of_stmts(handler.body))

            # Pop exception condition
            result.append(ast.Expr(
                value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_POP_CONDITION),
                lineno=0, col_offset=0,
            ))

            # Add to already_handled for next handler
            exception_cond_temps.append(cond_temp)

        # --- 3. else block ---
        if node.orelse:
            for cond in exception_cond_temps:
                result.append(ast.Expr(
                    value=self._emit_hook_call(
                        SidewinderHookNames.SIDEWINDER_CONDITION_FALSE,
                        ast.Name(id=cond, ctx=ast.Load())
                    ),
                    lineno=0, col_offset=0,
                ))

            result.extend(self._visit_list_of_stmts(node.orelse))

            for _ in exception_cond_temps:
                result.append(ast.Expr(
                    value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_POP_CONDITION),
                    lineno=0, col_offset=0,
                ))

        # --- 4. finally block ---
        if node.finalbody:
            result.extend(self._visit_list_of_stmts(node.finalbody))

        return result
    
    def visit_TryStar(self, node: ast.TryStar) -> Any:
        """Transform try-except* statement (exception groups)."""
        raise NotImplementedError(
            "except* (TryStar) not supported. "
            "Requires powerset path semantics — multiple handlers can fire simultaneously "
            "on the same ExceptionGroup, breaking the mutually exclusive path assumption "
            "in __sidewinder_merge__. Current model would produce imprecise over-approximation. "
            "See: PEP 654, Python 3.11+"
            f"Problematic node: {ast.unparse(node)}"
        )
    
    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> Any:
        """Transform exception handler."""
        raise SidewinderIllegalStateError("ExceptHandler should not be called, it should be handled directly in visit_Try and visit_TryStar (if implemented)")
