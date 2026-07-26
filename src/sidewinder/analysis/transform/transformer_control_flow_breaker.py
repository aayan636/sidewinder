import ast
from typing import Any, Union

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers
from sidewinder.analysis.symbolic.hook import SidewinderHookNames

class SidewinderControlFlowBreakerTransformerMixin(SidewinderTransformerHelpers):
    def visit_Return(self, node: ast.Return) -> Any:
        """Transform return statement - transform the return value."""
        lowered_value = self._visit_expr(node.value) if node.value else None
        ret = []
        ret.extend(lowered_value.stmts) if lowered_value else None
        ret.append(ast.Expr(value=self._emit_hook_call(
            SidewinderHookNames.SIDEWINDER_RETURN,
            lowered_value.expr if lowered_value else ast.Constant(value=None)
        ), lineno=0, col_offset=0))
        return ret
    
    def visit_Break(self, node: ast.Break) -> ast.Expr:
        """
        Transform break to explicit sidewinder call.
        
        break
        becomes:
        __sidewinder_break__(__sidewinder_state=__sidewinder_state)
        """
        return ast.Expr(
            value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_BREAK),
            lineno=0, col_offset=0,
        )

    def visit_Continue(self, node: ast.Continue) -> ast.Expr:
        """
        Transform continue to explicit sidewinder call.
        
        continue
        becomes:
        __sidewinder_continue__(__sidewinder_state=__sidewinder_state)
        """
        return ast.Expr(
            value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_CONTINUE),
            lineno=0, col_offset=0,
        )
    
    def visit_Raise(self, node: ast.Raise) -> ast.Expr:
        """
        Transform raise to explicit sidewinder call.
        
        raise exc
        becomes:
        __sidewinder_raise__(exc, __sidewinder_state=__sidewinder_state)
        
        raise exc from cause
        becomes:
        __sidewinder_raise__(exc, cause, __sidewinder_state=__sidewinder_state)
        
        raise  (bare re-raise)
        becomes:
        __sidewinder_raise__(__sidewinder_state=__sidewinder_state)
        """

        stmts = []
        args = []
        if node.exc is not None:
            lowered_exc = self._visit_expr(node.exc)
            args = [lowered_exc.expr]
            stmts.extend(lowered_exc.stmts)
            if node.cause is not None:
                lowered_cause = self._visit_expr(node.cause)
                args.append(lowered_cause.expr)
                stmts.extend(lowered_cause.stmts)

        return ast.Expr(
            value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_RAISE, *args),
            lineno=0, col_offset=0,
        )
 

    def visit_Yield(self, node: ast.Yield) -> Any:
        """Transform yield expression."""
        raise NotImplementedError("Yield is not yet supported")
    
    def visit_YieldFrom(self, node: ast.YieldFrom) -> Any:
        """Transform yield from expression."""
        raise NotImplementedError("Yield from is not yet supported")