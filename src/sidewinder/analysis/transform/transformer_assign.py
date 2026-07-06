import ast
import copy 

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers


class SidewinderAssignTransformerMixin(SidewinderTransformerHelpers):
    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        """Transform assignment statement - transform value."""
        transformed_value = self._visit_expr(node.value)
        if len(node.targets) != 1:
            raise NotImplementedError(f"Sidewinder currently only supports a single target for assign statements like {ast.unparse(node)}")
        to_return = []
        for target in node.targets:
            to_return.extend(self._visit_target(target, transformed_value))
        return to_return
    
    def visit_AnnAssign(self, node: ast.AnnAssign) -> list[ast.stmt]:
        """Transform annotated assignment statement."""
        # Transform the annotation (it's an expr)
        node.annotation = self._visit_expr(node.annotation)
        # Transform the value if it exists (can be None)
        if node.value is not None:
            return self._visit_target(node.target, self._visit_expr(node.value))
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

        read_target = copy.deepcopy(node.target)
        read_target.ctx = ast.Load()
        rhs_value = ast.Call(
            func=ast.Attribute(
                value=self._visit_expr(read_target),
                attr=method_name,
                ctx=ast.Load(),
            ),
            args=[self._visit_expr(node.value)],
            keywords=[
                ast.keyword(
                    arg='__sidewinder_state',
                    value=ast.Name(id='__sidewinder_state', ctx=ast.Load()),
                )
            ],
        )

        tmp = self._fresh_temp()
        to_return = []
        to_return.append(
            ast.Assign(
                targets=[ast.Name(id=tmp, ctx=ast.Store())],
                value=rhs_value,
                lineno=0, col_offset=0,
            )
        )
        to_return.extend(self._visit_target(node.target, ast.Name(id=tmp, ctx=ast.Load())))
        return to_return
