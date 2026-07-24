import ast

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers
from sidewinder.analysis.symbolic.hook import SidewinderHookNames

class SidewinderWhileTransformerMixin(SidewinderTransformerHelpers):
    def visit_While(self, node: ast.While) -> list[ast.stmt]:
        """
        while <condition>:
            <body>

        Becomes:

        __sidewinder_condN__ = <transformed_condition>          # first eval before loop
        __sidewinder_fixed_pointN__ = False
        while not __sidewinder_fixed_pointN__:
            __sidewinder_condition_true__(__sidewinder_condN__, __sidewinder_state__)
            <transformed body>
            __sidewinder_condN__ = __sidewinder_union__(__sidewinder_condN__, <transformed_condition>)
            __sidewinder_fixed_pointN__ = __sidewinder_fixed_point_check__(__sidewinder_state__)
            __sidewinder_pop_condition__(__sidewinder_state__)
        __sidewinder_condition_false__(__sidewinder_condN__, __sidewinder_state__)
        """
        if node.orelse:
            raise NotImplementedError("while/else not supported")

        result: list[ast.stmt] = []

        # __sidewinder_condN__ = <transformed_condition>
        cond_temp = self._fresh_temp("__sidewinder_cond")

        lowered_test = self._visit_expr(node.test)
        result.extend(lowered_test.stmts)

        result.append(ast.Assign(
            targets=[ast.Name(id=cond_temp, ctx=ast.Store())],
            value=lowered_test.expr,
            lineno=0, col_offset=0,
        ))

        # __sidewinder_fixed_pointN__ = False
        fixed_point_temp = self._fresh_temp("__sidewinder_fixed_point")
        result.append(ast.Assign(
            targets=[ast.Name(id=fixed_point_temp, ctx=ast.Store())],
            value=ast.Constant(value=False),
            lineno=0, col_offset=0,
        ))

        while_node = ast.While(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Name(id=fixed_point_temp, ctx=ast.Load())
            ),
            body=[],
            orelse=[],
            lineno=0, col_offset=0,
        )

        # TODO: REMOVE THIS APPEND TO CONTEXT NONSENSE
        with self.current_context.enter_context(while_node, "body") as c:
            # push true condition
            c.append_stmt(
                ast.Expr(value=self._emit_hook_call(
                    SidewinderHookNames.SIDEWINDER_CONDITION_TRUE,
                    ast.Name(id=cond_temp, ctx=ast.Load())
                ), lineno=0, col_offset=0)
            )

            # transformed body
            while_node.body.extend(self._visit_list_of_stmts(node.body))

            # union update condition
            lowered_second_test = self._visit_expr(node.test)
            for stmt in lowered_second_test.stmts:
                c.append_stmt(stmt)
            c.append_stmt(
                ast.Assign(
                    targets=[ast.Name(id=cond_temp, ctx=ast.Store())],
                    value=self._emit_hook_call(
                        SidewinderHookNames.SIDEWINDER_UNION,
                        ast.Name(id=cond_temp, ctx=ast.Load()),
                        lowered_second_test.expr,
                    ),
                    lineno=0, col_offset=0,
                )
            )

            # fixed point check
            c.append_stmt(
                ast.Assign(
                    targets=[ast.Name(id=fixed_point_temp, ctx=ast.Store())],
                    value=self._emit_hook_call(SidewinderHookNames.SIDEWINDER_FIXED_POINT),
                    lineno=0, col_offset=0,
                )
            )

            c.append_stmt(
                ast.Expr(value=self._emit_hook_call(
                    SidewinderHookNames.SIDEWINDER_POP_CONDITION,
                ), lineno=0, col_offset=0),
            )

        result.append(while_node)

        # push false condition after loop — no pop
        result.append(ast.Expr(
            value=self._emit_hook_call(
                SidewinderHookNames.SIDEWINDER_CONDITION_FALSE,
                ast.Name(id=cond_temp, ctx=ast.Load())
            ),
            lineno=0, col_offset=0
        ))

        return result