import ast

from analysis.transform.transformer_helpers import SidewinderTransformerHelpers
from analysis.symbolic.hook import SidewinderHookNames

class SidewinderIfTransformerMixin(SidewinderTransformerHelpers):
    def visit_If(self, node: ast.If) -> list[ast.stmt]:
        result: list[ast.stmt] = []
        
        # t = <transformed condition>
        temp = self._fresh_temp("__sidewinder_cond")
        transformed_test = self._visit_expr(node.test)
        result.append(ast.Assign(
            targets=[ast.Name(id=temp, ctx=ast.Store())],
            value=transformed_test,
            lineno=0, col_offset=0,
        ))

        # sidewinder_push_true_condition(t, __sidewinder_state)
        result.append(ast.Expr(
            value=self._emit_hook_call(
                SidewinderHookNames.SIDEWINDER_CONDITION_TRUE,
                ast.Name(id=temp, ctx=ast.Load())
            ),
            lineno=0, col_offset=0
        ))

        # <transformed if block>
        result.extend(self._visit_list_of_stmts(node.body))

        # sidewinder_pop_condition(__sidewinder_state)
        result.append(ast.Expr(
            value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_POP_CONDITION),
            lineno=0, col_offset=0
        ))

        if node.orelse:
            # sidewinder_push_false_condition(t, __sidewinder_state)
            result.append(ast.Expr(
                value=self._emit_hook_call(
                    SidewinderHookNames.SIDEWINDER_CONDITION_FALSE,
                    ast.Name(id=temp, ctx=ast.Load())
                ),
                lineno=0, col_offset=0
            ))

            # <transformed else block> (empty if no else)
        
            result.extend(self._visit_list_of_stmts(node.orelse))

            # sidewinder_pop_condition(__sidewinder_state)
            result.append(ast.Expr(
                value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_POP_CONDITION),
                lineno=0, col_offset=0
            ))

        return result