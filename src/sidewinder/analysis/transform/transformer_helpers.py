import ast
from typing import Dict, List, Any, Optional, Set, Union, overload, TypeVar
from collections import defaultdict
import copy

from sidewinder.analysis.transform.transformer_base import SidewinderTransformerBase, T, LoweredExpr
from sidewinder.analysis.transform.transformer_context import TransformerContext
from sidewinder.analysis.transform.errors import SidewinderIllegalStateError
from sidewinder.analysis.symbolic.hook import SidewinderHookNames


class SidewinderTransformerHelpers(SidewinderTransformerBase):
    def _fresh_temp(self, prefix: str = "__t") -> str:
        """Generate a fresh temporary variable name."""
        name = f"{prefix}{self.temp_counter}"
        self.temp_counter += 1
        return name
    
    def _make_sidewinder_state_param(self) -> ast.arg:
        """Create the __sidewinder_state parameter with type annotation."""
        return ast.arg(
            arg="__sidewinder_state",
            annotation=ast.Name(id="SidewinderState", ctx=ast.Load())
        )
    
    def _sidewinder_state_keyword(self) -> ast.keyword:
        """Create the __sidewinder_state keyword argument for hook calls."""
        return ast.keyword(
            arg="__sidewinder_state",
            value=ast.Name(id="__sidewinder_state", ctx=ast.Load())
        )
    
    def _emit_hook_call(
        self,
        hook: SidewinderHookNames,
        *args: ast.expr,
        extra_kwargs: Optional[Dict[str, ast.expr]] = None
    ) -> ast.Call:
        """Create a sidewinder hook call with __sidewinder_state__ threaded through."""
        keywords = [
            ast.keyword(arg=k, value=v) for k, v in (extra_kwargs or {}).items()
        ] + [self._sidewinder_state_keyword()]
        return ast.Call(
            func=ast.Name(id=f"__{hook.name.lower()}__", ctx=ast.Load()),
            args=list(args),
            keywords=keywords,
        )

    def _emit_method_hook_call(
        self,
        obj: ast.expr,
        hook: SidewinderHookNames,
        *args: ast.expr,
        extra_kwargs: Optional[Dict[str, ast.expr]] = None
    ) -> ast.Call:
        """Create a sidewinder hook call as a method on an object.
        
        obj.__sidewinder_hook__(*args, __sidewinder_state__=__sidewinder_state__)
        """
        keywords = [
            ast.keyword(arg=k, value=v) for k, v in (extra_kwargs or {}).items()
        ] + [self._sidewinder_state_keyword()]
        return ast.Call(
            func=ast.Attribute(
                value=obj,
                attr=f"__{hook.name.lower()}__",
                ctx=ast.Load()
            ),
            args=list(args),
            keywords=keywords,
        )

    def _visit_list_of_stmts(self, stmts: List[ast.stmt]) -> List[ast.stmt]:
        """
        Visit a list of statements, handling list expansion and preamble injection.
        Must be called within a context manager.
        """
        result: list[ast.stmt] = []
        for stmt in stmts:
            visited = self.visit(stmt)
            if isinstance(visited, list):
                result.extend(visited)
            else:
                result.append(visited)
        return result
    
    def _visit_expr(self, expr: T) -> LoweredExpr:
        generated_stmts, final_expr = self.visit(expr)
        return LoweredExpr(stmts=generated_stmts, expr=final_expr)
    
    def _visit_target(self, target: ast.expr | ast.Tuple | ast.List, visited_rhs: ast.expr) -> List[ast.stmt]:
        """
        Emit statements to assign rhs to target.
        rhs is already a normalized expression (usually a Name node pointing to a tmp).
        Appends statements to current_context, returns nothing.
        """
        assert isinstance(target, (ast.Name, ast.Attribute, ast.Subscript, ast.Tuple, ast.List, ast.Starred)), f"_visit_target called with a unexpected node type: {ast.dump(target)}"
        assert hasattr(target, "ctx"), f"Something changed in the Python spec.... the node {ast.dump(target)} has no ctx attribute"

        assert isinstance(target.ctx, ast.Store), f"_visit_target called on non-Store target: {ast.dump(target)}"

        match target: 
            case ast.Name():
                # x = rhs  — base case, plain assignment, no transformation needed
                return [ast.Assign(targets=[target], value=visited_rhs, lineno=0, col_offset=0)]

            case ast.Attribute():
                # y.attr = rhs  →  _visit_expr(y).__setattr__("attr", rhs)
                obj = self._visit_expr(target.value)
                return [
                    ast.Expr(value=ast.Call(
                        func=ast.Attribute(value=obj, attr="__sidewinder_setattr__", ctx=ast.Load()),
                        args=[ast.Constant(value = target.attr), visited_rhs],
                        keywords=[],
                    ), lineno=0, col_offset=0)
                ]

            case ast.Subscript():
                # y[i] = rhs  →  _visit_expr(y).__setitem__(_visit_expr(i), rhs)
                obj = self._visit_expr(target.value)
                idx = self._visit_expr(target.slice)
                return [
                    ast.Expr(value=ast.Call(
                        func=ast.Attribute(value=obj, attr="__sidewinder_setitem__", ctx=ast.Load()),
                        args=[idx, visited_rhs],
                        keywords=[],
                    ), lineno=0, col_offset=0)
                ]

            case ast.Tuple() | ast.List():
                to_return = []

                starred_indices = [i for i, e in enumerate(target.elts)
                                if isinstance(e, ast.Starred)]

                if len(starred_indices) == 0:
                    # simple case: x, y, z = rhs
                    # emit: _iter = visited_rhs.__iter__()
                    iter_tmp = self._fresh_temp()
                    to_return.append(
                        ast.Assign(
                            targets=[ast.Name(id=iter_tmp, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Attribute(value=visited_rhs, attr="__iter__", ctx=ast.Load()),
                                args=[], keywords=[],
                            ),
                            lineno=0, col_offset=0,
                        )
                    )
                    for elt in target.elts:
                        # emit: _tmpN = _iter.__next__()
                        next_tmp = self._fresh_temp()
                        to_return.append(
                            ast.Assign(
                                targets=[ast.Name(id=next_tmp, ctx=ast.Store())],
                                value=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(id=iter_tmp, ctx=ast.Load()),
                                        attr="__next__",
                                        ctx=ast.Load(),
                                    ),
                                    args=[], keywords=[],
                                ),
                                lineno=0, col_offset=0,
                            )
                        )
                        assert False, "This does not look right, fix when you get to it"
                        self._visit_target(elt, ast.Name(id=next_tmp, ctx=ast.Load()))
                    return to_return

                elif len(starred_indices) == 1:
                    raise NotImplementedError("starred unpacking in tuple target")

                else:
                    raise ValueError("multiple starred targets in unpacking — illegal Python")

            case ast.Starred():
                # should only appear inside Tuple/List, never as a top-level target
                # e.g.  *x = rhs  is illegal Python
                raise ValueError("starred target outside of tuple unpacking")

            case _:
                # anything else: func() = rhs, (x + y) = rhs, literal = rhs etc.
                raise NotImplementedError(f"unsupported assignment target: {ast.dump(target)}")
