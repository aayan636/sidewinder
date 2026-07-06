import ast
from typing import Any, Union

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers

class SidewinderFunctionTransformerMixin(SidewinderTransformerHelpers):
    # ========== Function (sync and async) Def Nodes ==========

    def _transform_function_def(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Any:
        """
        Transform function definition to include __sidewinder_state parameter.
        Works for both regular and async functions.
        
        Strategy: ALWAYS add __sidewinder_state as a keyword-only argument.
        
        Why keyword-only?
        1. Consistent call sites: always use __sidewinder_state=state (no signature tracking needed)
        2. Automatic correct placement: kwonlyargs come after *args and before **kwargs
        3. No positional ambiguity: can't accidentally pass wrong number of args
        
        Results in:
        - def foo(x, y):              → def foo(x, y, *, __sidewinder_state):
        - def foo(x, *args):          → def foo(x, *args, __sidewinder_state):  
        - def foo(x, **kw):           → def foo(x, *, __sidewinder_state, **kw):
        - def foo(x, *args, **kw):    → def foo(x, *args, __sidewinder_state, **kw):
        
        All call sites become: func(..., __sidewinder_state=__sidewinder_state)
        """
        # Check if function has **kwargs
        has_kwargs = node.args.kwarg is not None
        self.function_signatures[node.name] = has_kwargs
        
        # Create the state parameter
        state_param = self._make_sidewinder_state_param()
    
        # Add to kwonlyargs (before **kwargs)
        node.args.kwonlyargs.append(state_param)
        # Add None default for the new kwonly arg
        if node.args.kw_defaults is None:
            node.args.kw_defaults = []
        node.args.kw_defaults.append(None)
        
        # Transform function body
        # TODO: Fixed point statement must be added
        with self.current_context.enter_context(node, "body") as c:
            node.body = self._visit_list_of_stmts(node.body)
        
        # Transform decorators
        node.decorator_list = [self._visit_expr(dec) for dec in node.decorator_list]     
        
        return node
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        """Visit a function definition."""
        return self._transform_function_def(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        """Visit an async function definition."""
        return self._transform_function_def(node)