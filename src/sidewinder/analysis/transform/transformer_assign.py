import ast
import copy 

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers


class SidewinderAssignTransformerMixin(SidewinderTransformerHelpers):
    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        """Transform assignment statement - transform value."""
        lowered_value = self._visit_expr(node.value)
        if len(node.targets) != 1:
            raise NotImplementedError(f"Sidewinder currently only supports a single target for assign statements like {ast.unparse(node)}")
        to_return = []
        to_return.extend(lowered_value.stmts)
        for target in node.targets:
            to_return.extend(self._visit_target(target, lowered_value.expr))
        return to_return
    
    def visit_AnnAssign(self, node: ast.AnnAssign) -> list[ast.stmt]:
        """Transform annotated assignment statement."""
        # Transform the annotation (it's an expr)
        stmts = []
        lowered_annotation = self._visit_expr(node.annotation)
        node.annotation = lowered_annotation.expr
        stmts.extend(lowered_annotation.stmts)
        # Transform the value if it exists (can be None)
        if node.value is not None:
            lowered_value = self._visit_expr(node.value)
            stmts.append(lowered_value.stmts)
            return stmts + self._visit_target(node.target, lowered_value.expr)
        return []
    
    def visit_AugAssign(self, node: ast.AugAssign) -> list[ast.stmt]:
        op_map = {
            ast.Add:      'add',
            ast.Sub:      'sub',
            ast.Mult:     'mul',
            ast.Div:      'truediv',
            ast.FloorDiv: 'floordiv',
            ast.Mod:      'mod',
            ast.Pow:      'pow',
            ast.LShift:   'lshift',
            ast.RShift:   'rshift',
            ast.BitOr:    'or',
            ast.BitXor:   'xor',
            ast.BitAnd:   'and',
            ast.MatMult:  'matmul',
        }

        op_name = op_map.get(type(node.op))
        if not op_name:
            raise NotImplementedError(f"Unhandled op: {node.op}")

        method_name = f'__sidewinder_i{op_name}__'

        to_return = []

        read_target = copy.deepcopy(node.target)
        lowered_read_target = self._visit_expr(read_target)
        to_return.extend(lowered_read_target.stmts)
        read_target.ctx = ast.Load()

        lowered_value = self._visit_expr(node.value)
        to_return.extend(lowered_value.stmts)
        rhs_value = ast.Call(
            func=ast.Attribute(
                value=lowered_read_target.expr,
                attr=method_name,
                ctx=ast.Load(),
            ),
            args=[lowered_value.expr],
            keywords=[
                ast.keyword(
                    arg='__sidewinder_state',
                    value=ast.Name(id='__sidewinder_state', ctx=ast.Load()),
                )
            ],
        )

        tmp = self._fresh_temp()
        
        to_return.append(
            ast.Assign(
                targets=[ast.Name(id=tmp, ctx=ast.Store())],
                value=rhs_value,
                lineno=0, col_offset=0,
            )
        )
        to_return.extend(self._visit_target(node.target, ast.Name(id=tmp, ctx=ast.Load())))
        return to_return
