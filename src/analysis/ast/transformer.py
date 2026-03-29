"""
Sidewinder AST Transformer for Python 3.12

This module transforms Python code for symbolic execution by:
1. Injecting __sidewinder_state parameter into all function definitions
2. Injecting __sidewinder_state argument into all function calls
3. Desugaring all syntactic sugar to explicit method calls
4. Converting all operations to __sidewinder_* methods
"""

import ast
from typing import Dict, List, Any, Optional, Set, Union, overload, TypeVar
from collections import defaultdict
import copy

from analysis.ast.transformer_context import TransformerContext


class SidewinderTransformer(ast.NodeTransformer):
    """
    Transforms Python AST for Sidewinder symbolic execution.
    
    Key transformations:
    - Thread SidewinderState through all functions
    - Desugar operators to __sidewinder_* method calls
    - Expand for loops to explicit iterator protocol
    - Convert comprehensions to explicit loops
    - Desugar with statements to __enter__/__exit__
    """
    def generic_visit(self, node: ast.AST) -> None:
        raise NotImplementedError("All visitor methods must be implemented and not delegated to generic_visit of ast.NodeTransformer")

    def __init__(self):
        # Track which functions have **kwargs in their signature
        self.function_signatures: Dict[str, bool] = {}  # name -> has_kwargs
        
        # Counter for generating fresh temporary variable names
        self.temp_counter = 0
        
        # Track current scope for variable naming
        self.current_scope = []

        # Current node where we append extra computation required
        self.current_context = TransformerContext()
        
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
    
    T = TypeVar('T', bound=ast.expr)

    def _visit_expr(self, expr: T) -> T:
        generated_stmts, final_expr = self.visit(expr)
        for stmt in generated_stmts:
            self.current_context.append_stmt(stmt)
        return final_expr
    
    def _visit_target(self, target: ast.expr | ast.Tuple | ast.List, visited_rhs: ast.expr) -> None:
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
                self.current_context.append_stmt(ast.Assign(targets=[target], value=visited_rhs, lineno=0, col_offset=0))

            case ast.Attribute():
                # y.attr = rhs  →  _visit_expr(y).__setattr__("attr", rhs)
                obj = self._visit_expr(target.value)
                self.current_context.append_stmt(
                    ast.Expr(value=ast.Call(
                        func=ast.Attribute(value=obj, attr="__sidewinder_setattr__", ctx=ast.Load()),
                        args=[ast.Constant(value = target.attr), visited_rhs],
                        keywords=[],
                    ), lineno=0, col_offset=0)
                )

            case ast.Subscript():
                # y[i] = rhs  →  _visit_expr(y).__setitem__(_visit_expr(i), rhs)
                obj = self._visit_expr(target.value)
                idx = self._visit_expr(target.slice)
                self.current_context.append_stmt(
                    ast.Expr(value=ast.Call(
                        func=ast.Attribute(value=obj, attr="__sidewinder_setitem__", ctx=ast.Load()),
                        args=[idx, visited_rhs],
                        keywords=[],
                    ), lineno=0, col_offset=0)
                )

            case ast.Tuple() | ast.List():
                starred_indices = [i for i, e in enumerate(target.elts)
                                if isinstance(e, ast.Starred)]

                if len(starred_indices) == 0:
                    # simple case: x, y, z = rhs
                    # emit: _iter = visited_rhs.__iter__()
                    iter_tmp = self._fresh_temp()
                    self.current_context.append_stmt(
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
                        self.current_context.append_stmt(
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
                        self._visit_target(elt, ast.Name(id=next_tmp, ctx=ast.Load()))

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


    # ========== Overloads for type hinting =============

    @overload
    def visit(self, node: ast.stmt) -> Union[ast.stmt, List[ast.stmt]]: ...

    @overload
    def visit(self, node: T) -> tuple[List[ast.stmt], T]: ...

    def visit(self, node: ast.AST) -> Any:
        return super().visit(node)

    # ========== Module Nodes ==========
    
    def visit_Module(self, node: ast.Module) -> Any:
        """Visit a module node - add import for SidewinderState."""
        # Add import: from sidewinder.analysis.symbolic.state import SidewinderState
        import_node = ast.ImportFrom(
            module="sidewinder.analysis.symbolic.state",
            names=[ast.alias(name="SidewinderState", asname=None)],
            level=0
        )
        
        # Transform all statements in the module
        with self.current_context.enter_context(node, "body") as c:
            node.body = [import_node] + self._visit_list_of_stmts(node.body)
        return node
    
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
    
    # ========== Class Def Nodes ==========
    
    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        """Visit a class definition - transform all methods."""
        self.current_scope.append(node.name)
        
        # Transform class body
        node.body = self._visit_list_of_stmts(node.body)
        
        # Transform decorators
        node.decorator_list = [self._visit_expr(dec) for dec in node.decorator_list]
        # Transform bases
        node.bases = [self._visit_expr(bas) for bas in node.bases]
        # Transform keywords
        for kw in node.keywords:
            kw.value = self._visit_expr(kw.value)
        
        self.current_scope.pop()
        return node
    
    def visit_Return(self, node: ast.Return) -> Any:
        """Transform return statement - transform the return value."""
        if node.value:
            node.value = self._visit_expr(node.value)
        return node
    
    def visit_Delete(self, node: ast.Delete) -> Any:
        """Transform del statement."""
        new_targets = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Case 1: del variable_name
                # Just a name binding removal - keep as is
                new_targets.append(target)
            else:
                raise NotImplementedError("TBI")
                # TODO: Should del x become x.__sidewinder_del__(__sidewinder_state)?
            
        node.targets = new_targets
        return node
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Transform assignment statement - transform value."""
        transformed_value = self._visit_expr(node.value)
        if len(node.targets) != 1:
            raise NotImplementedError(f"Sidewinder currently only supports a single target for assign statements like {ast.unparse(node)}")
        for target in node.targets:
            self._visit_target(target, transformed_value)
        return None
    
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Transform annotated assignment statement."""
        # Transform the annotation (it's an expr)
        node.annotation = self._visit_expr(node.annotation)
        # Transform the value if it exists (can be None)
        if node.value is not None:
            self._visit_target(node.target, self._visit_expr(node.value))
        return None
    
    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
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
        self.current_context.append_stmt(
            ast.Assign(
                targets=[ast.Name(id=tmp, ctx=ast.Store())],
                value=rhs_value,
                lineno=0, col_offset=0,
            )
        )
        self._visit_target(node.target, ast.Name(id=tmp, ctx=ast.Load()))

    
    def visit_For(self, node: ast.For) -> Any:
        """
        Transform for loop to explicit iterator protocol.
        
        for item in iterable:
            body
        
        Becomes:
        __iter = iterable.__sidewinder_iter__(__sidewinder_state)
        while True:
            try:
                item = __iter.__sidewinder_next__(__sidewinder_state)
                body
            except StopIteration:
                break
        """
        iter_var = self._fresh_temp("__iter")
        
        # Create: __iter = iterable.__sidewinder_iter__(__sidewinder_state)
        iter_assign = ast.Assign(
            targets=[ast.Name(id=iter_var, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=self.visit(node.iter),
                    attr='__sidewinder_iter__',
                    ctx=ast.Load()
                ),
                args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                keywords=[]
            )
        )
        
        # Create: item = __iter.__sidewinder_next__(__sidewinder_state)
        next_assign = ast.Assign(
            targets=[node.target],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=iter_var, ctx=ast.Load()),
                    attr='__sidewinder_next__',
                    ctx=ast.Load()
                ),
                args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                keywords=[]
            )
        )
        
        # Transform loop body
        body = [self.visit(stmt) for stmt in node.body]
        
        # Create the try-except block
        try_block = ast.Try(
            body=[next_assign] + body,
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id='StopIteration', ctx=ast.Load()),
                    name=None,
                    body=[ast.Break()]
                )
            ],
            orelse=[],
            finalbody=[]
        )
        
        # Create the while True loop
        while_loop = ast.While(
            test=ast.Constant(value=True),
            body=[try_block],
            orelse=[self.visit(stmt) for stmt in node.orelse] if node.orelse else []
        )
        
        return [iter_assign, while_loop]
    
    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:
        """
        Transform async for loop to explicit async iterator protocol.
        
        async for item in iterable:
            body
        
        Becomes:
        __aiter = iterable.__sidewinder_aiter__(__sidewinder_state)
        while True:
            try:
                item = await __aiter.__sidewinder_anext__(__sidewinder_state)
                body
            except StopAsyncIteration:
                break
        """
        # TODO: Similar to visit_For but with __aiter__/__anext__ and await
        aiter_var = self._fresh_temp("__aiter")
        
        # Create: __aiter = iterable.__sidewinder_aiter__(__sidewinder_state)
        aiter_assign = ast.Assign(
            targets=[ast.Name(id=aiter_var, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=self.visit(node.iter),
                    attr='__sidewinder_aiter__',
                    ctx=ast.Load()
                ),
                args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                keywords=[]
            )
        )
        
        # Create: item = await __aiter.__sidewinder_anext__(__sidewinder_state)
        next_assign = ast.Assign(
            targets=[node.target],
            value=ast.Await(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=aiter_var, ctx=ast.Load()),
                        attr='__sidewinder_anext__',
                        ctx=ast.Load()
                    ),
                    args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                    keywords=[]
                )
            )
        )
        
        # Transform loop body
        body = [self.visit(stmt) for stmt in node.body]
        
        # Create the try-except block
        try_block = ast.Try(
            body=[next_assign] + body,
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id='StopAsyncIteration', ctx=ast.Load()),
                    name=None,
                    body=[ast.Break()]
                )
            ],
            orelse=[],
            finalbody=[]
        )
        
        # Create the while True loop
        while_loop = ast.While(
            test=ast.Constant(value=True),
            body=[try_block],
            orelse=[self.visit(stmt) for stmt in node.orelse] if node.orelse else []
        )
        
        return [aiter_assign, while_loop]
    
    def visit_While(self, node: ast.While) -> Any:
        """Transform while loop - transform condition and body."""
        node.test = self.visit(node.test)
        node.body = [self.visit(stmt) for stmt in node.body]
        node.orelse = [self.visit(stmt) for stmt in node.orelse]
        return node
    
    def visit_If(self, node: ast.If) -> Any:
        """Transform if statement - transform condition and bodies."""
        node.test = self.visit(node.test)
        node.body = [self.visit(stmt) for stmt in node.body]
        node.orelse = [self.visit(stmt) for stmt in node.orelse]
        return node
    
    def visit_With(self, node: ast.With) -> Any:
        """
        Transform with statement to explicit __enter__/__exit__ calls.
        
        with expr as var:
            body
        
        Becomes:
        __ctx = expr
        var = __ctx.__sidewinder_enter__(__sidewinder_state)
        try:
            body
        finally:
            __ctx.__sidewinder_exit__(__sidewinder_state, None, None, None)
        """
        # TODO: Handle multiple context managers
        # TODO: Handle exception info passing to __exit__
        
        statements = []
        
        for item in node.items:
            ctx_var = self._fresh_temp("__ctx")
            
            # __ctx = expr
            ctx_assign = ast.Assign(
                targets=[ast.Name(id=ctx_var, ctx=ast.Store())],
                value=self.visit(item.context_expr)
            )
            statements.append(ctx_assign)
            
            # var = __ctx.__sidewinder_enter__(__sidewinder_state)
            if item.optional_vars:
                enter_assign = ast.Assign(
                    targets=[item.optional_vars],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=ctx_var, ctx=ast.Load()),
                            attr='__sidewinder_enter__',
                            ctx=ast.Load()
                        ),
                        args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                        keywords=[]
                    )
                )
                statements.append(enter_assign)
            else:
                # Just call __enter__ without assignment
                enter_call = ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=ctx_var, ctx=ast.Load()),
                            attr='__sidewinder_enter__',
                            ctx=ast.Load()
                        ),
                        args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                        keywords=[]
                    )
                )
                statements.append(enter_call)
            
            # Transform body
            body = [self.visit(stmt) for stmt in node.body]
            
            # __ctx.__sidewinder_exit__(__sidewinder_state, None, None, None)
            exit_call = ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=ctx_var, ctx=ast.Load()),
                        attr='__sidewinder_exit__',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Name(id='__sidewinder_state', ctx=ast.Load()),
                        ast.Constant(value=None),
                        ast.Constant(value=None),
                        ast.Constant(value=None)
                    ],
                    keywords=[]
                )
            )
            
            # Create try-finally
            try_finally = ast.Try(
                body=body,
                handlers=[],
                orelse=[],
                finalbody=[exit_call]
            )
            statements.append(try_finally)
        
        return statements if len(statements) > 1 else statements[0]
    
    def visit_AsyncWith(self, node: ast.AsyncWith) -> Any:
        """Transform async with statement - similar to with but with __aenter__/__aexit__."""
        # TODO: Similar to visit_With but with __sidewinder_aenter__/__sidewinder_aexit__ and await
        statements = []
        
        for item in node.items:
            ctx_var = self._fresh_temp("__actx")
            
            ctx_assign = ast.Assign(
                targets=[ast.Name(id=ctx_var, ctx=ast.Store())],
                value=self.visit(item.context_expr)
            )
            statements.append(ctx_assign)
            
            if item.optional_vars:
                enter_assign = ast.Assign(
                    targets=[item.optional_vars],
                    value=ast.Await(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id=ctx_var, ctx=ast.Load()),
                                attr='__sidewinder_aenter__',
                                ctx=ast.Load()
                            ),
                            args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                            keywords=[]
                        )
                    )
                )
                statements.append(enter_assign)
            
            body = [self.visit(stmt) for stmt in node.body]
            
            exit_call = ast.Expr(
                value=ast.Await(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=ctx_var, ctx=ast.Load()),
                            attr='__sidewinder_aexit__',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Name(id='__sidewinder_state', ctx=ast.Load()),
                            ast.Constant(value=None),
                            ast.Constant(value=None),
                            ast.Constant(value=None)
                        ],
                        keywords=[]
                    )
                )
            )
            
            try_finally = ast.Try(
                body=body,
                handlers=[],
                orelse=[],
                finalbody=[exit_call]
            )
            statements.append(try_finally)
        
        return statements if len(statements) > 1 else statements[0]
    
    def visit_Raise(self, node: ast.Raise) -> Any:
        """Transform raise statement."""
        if node.exc:
            node.exc = self.visit(node.exc)
        if node.cause:
            node.cause = self.visit(node.cause)
        return node
    
    def visit_Try(self, node: ast.Try) -> Any:
        """Transform try statement."""
        node.body = [self.visit(stmt) for stmt in node.body]
        node.handlers = [self.visit(handler) for handler in node.handlers]
        node.orelse = [self.visit(stmt) for stmt in node.orelse]
        node.finalbody = [self.visit(stmt) for stmt in node.finalbody]
        return node
    
    def visit_TryStar(self, node: ast.TryStar) -> Any:
        """Transform try-except* statement (exception groups)."""
        node.body = [self.visit(stmt) for stmt in node.body]
        node.handlers = [self.visit(handler) for handler in node.handlers]
        node.orelse = [self.visit(stmt) for stmt in node.orelse]
        node.finalbody = [self.visit(stmt) for stmt in node.finalbody]
        return node
    
    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> Any:
        """Transform exception handler."""
        if node.type:
            node.type = self.visit(node.type)
        node.body = [self.visit(stmt) for stmt in node.body]
        return node
    
    def visit_Assert(self, node: ast.Assert) -> Any:
        """Transform assert statement."""
        node.test = self.visit(node.test)
        if node.msg:
            node.msg = self.visit(node.msg)
        return node
    
    def visit_Import(self, node: ast.Import) -> Any:
        """Import statements pass through unchanged."""
        return node
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        """From-import statements pass through unchanged."""
        return node
    
    def visit_Global(self, node: ast.Global) -> Any:
        """Global statements pass through unchanged."""
        return node
    
    def visit_Nonlocal(self, node: ast.Nonlocal) -> Any:
        """Nonlocal statements pass through unchanged."""
        return node
    
    def visit_Expr(self, node: ast.Expr) -> Any:
        """Transform expression statement."""
        node.value = self.visit(node.value)
        return node
    
    def visit_Pass(self, node: ast.Pass) -> Any:
        """Pass statements are unchanged."""
        return node
    
    def visit_Break(self, node: ast.Break) -> Any:
        """Break statements are unchanged."""
        return node
    
    def visit_Continue(self, node: ast.Continue) -> Any:
        """Continue statements are unchanged."""
        return node
    
    def visit_Match(self, node: ast.Match) -> Any:
        """Transform match statement."""
        # TODO: Match statements need complex desugaring
        node.subject = self.visit(node.subject)
        node.cases = [self.visit(case) for case in node.cases]
        return node
    
    def visit_TypeAlias(self, node: ast.TypeAlias) -> Any:
        """Transform type alias statement."""
        node.name = self.visit(node.name)
        node.value = self.visit(node.value)
        if node.type_params:
            node.type_params = [self.visit(tp) for tp in node.type_params]
        return node
    
    # ========== Expression Nodes ==========
    
    def visit_BinOp(self, node: ast.BinOp) -> Any:
        """
        Transform binary operation to method call.
        
        a + b -> a.__sidewinder_add__(b, __sidewinder_state)
        """
        op_map = {
            ast.Add: 'add',
            ast.Sub: 'sub',
            ast.Mult: 'mult',
            ast.Div: 'truediv',
            ast.FloorDiv: 'floordiv',
            ast.Mod: 'mod',
            ast.Pow: 'pow',
            ast.LShift: 'lshift',
            ast.RShift: 'rshift',
            ast.BitOr: 'or',
            ast.BitXor: 'xor',
            ast.BitAnd: 'and',
            ast.MatMult: 'matmul',
        }
        
        op_name = op_map.get(type(node.op))
        if not op_name:
            # Fallback
            return node
        
        method_name = f'__sidewinder_{op_name}__'
        
        return ast.Call(
            func=ast.Attribute(
                value=self.visit(node.left),
                attr=method_name,
                ctx=ast.Load()
            ),
            args=[self.visit(node.right), ast.Name(id='__sidewinder_state', ctx=ast.Load())],
            keywords=[]
        )
    
    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        """
        Transform unary operation to method call.
        
        -a -> a.__sidewinder_neg__(__sidewinder_state)
        """
        op_map = {
            ast.UAdd: 'pos',
            ast.USub: 'neg',
            ast.Not: 'not',  # Note: not is actually __sidewinder_bool__ then negation
            ast.Invert: 'invert',
        }
        
        op_name = op_map.get(type(node.op))
        if not op_name:
            return node
        
        # Special case for 'not' - it's not a dunder method
        if op_name == 'not':
            # TODO: 'not x' should become something like: not x.__sidewinder_bool__(__sidewinder_state)
            # For now, just transform the operand
            return ast.UnaryOp(op=node.op, operand=self.visit(node.operand))
        
        method_name = f'__sidewinder_{op_name}__'
        
        return ast.Call(
            func=ast.Attribute(
                value=self.visit(node.operand),
                attr=method_name,
                ctx=ast.Load()
            ),
            args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
            keywords=[]
        )
    
    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        """
        Transform boolean operation.
        
        a and b -> short-circuit evaluation with __sidewinder_bool__
        a or b -> short-circuit evaluation with __sidewinder_bool__
        """
        # TODO: and/or need special handling for short-circuit semantics
        # For now, just transform the operands
        node.values = [self.visit(val) for val in node.values]
        return node
    
    def visit_Compare(self, node: ast.Compare) -> Any:
        """
        Transform comparison operation.
        
        a < b -> a.__sidewinder_lt__(b, __sidewinder_state)
        a == b -> a.__sidewinder_eq__(b, __sidewinder_state)
        """
        op_map = {
            ast.Eq: 'eq',
            ast.NotEq: 'ne',
            ast.Lt: 'lt',
            ast.LtE: 'le',
            ast.Gt: 'gt',
            ast.GtE: 'ge',
            ast.Is: 'is',  # Note: 'is' is not a method, it's identity check
            ast.IsNot: 'is_not',
            ast.In: 'contains',  # Note: reversed - b.__contains__(a)
            ast.NotIn: 'not_contains',
        }
        
        # For simplicity, handle single comparison first
        # TODO: Chain comparisons (a < b < c) need multiple method calls
        if len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            op_name = op_map.get(type(op))
            
            if op_name in ['is', 'is_not']:
                # 'is' and 'is not' are identity checks, not method calls
                # Transform operands but keep the operator
                node.left = self.visit(node.left)
                node.comparators = [self.visit(comp) for comp in node.comparators]
                return node
            
            if op_name in ['contains', 'not_contains']:
                # 'in' is reversed: a in b -> b.__contains__(a)
                method_name = '__sidewinder_contains__'
                result = ast.Call(
                    func=ast.Attribute(
                        value=self.visit(node.comparators[0]),
                        attr=method_name,
                        ctx=ast.Load()
                    ),
                    args=[self.visit(node.left), ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                    keywords=[]
                )
                
                if op_name == 'not_contains':
                    # Negate the result
                    # TODO: Should this be __sidewinder_not__ or Python's 'not'?
                    result = ast.UnaryOp(op=ast.Not(), operand=result)
                
                return result
            
            if op_name:
                method_name = f'__sidewinder_{op_name}__'
                return ast.Call(
                    func=ast.Attribute(
                        value=self.visit(node.left),
                        attr=method_name,
                        ctx=ast.Load()
                    ),
                    args=[self.visit(node.comparators[0]), ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                    keywords=[]
                )
        
        # Multiple comparisons - transform each operand
        node.left = self.visit(node.left)
        node.comparators = [self.visit(comp) for comp in node.comparators]
        return node
    
    def visit_Call(self, node: ast.Call) -> Any:
        """
        Transform function call to include __sidewinder_state.
        
        func(a, b) -> func(a, b, __sidewinder_state)
        func(a, x=b) -> func(a, __sidewinder_state, x=b) [if func has **kwargs]
        """
        # Transform the function expression
        node.func = self.visit(node.func)
        
        # Transform arguments
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [self.visit(kw) for kw in node.keywords]
        
        # Check if this call has keyword arguments
        has_call_kwargs = len(node.keywords) > 0
        
        # Inject __sidewinder_state
        # TODO: We need to know if the target function has **kwargs to place state correctly
        # For now, assume no **kwargs and add state as last positional arg
        state_arg = ast.Name(id='__sidewinder_state', ctx=ast.Load())
        
        if has_call_kwargs:
            # If call has keyword args, add state before them
            # This might not always be correct - we'd need signature info
            node.args.append(state_arg)
        else:
            # No keyword args, add state as last positional
            node.args.append(state_arg)
        
        return node
    
    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """
        Transform attribute access to method call.
        
        a.b -> a.__sidewinder_getattribute__("b", __sidewinder_state)
        
        For chained access a.b.c, this recursively becomes:
        __t1 = a.__sidewinder_getattribute__("b", __sidewinder_state)
        __t2 = __t1.__sidewinder_getattribute__("c", __sidewinder_state)
        """
        # TODO: Attribute access returns expression, but we need statements for temps
        # This might need to be handled at a higher level (statement context)
        
        # For now, just do inline transformation
        return ast.Call(
            func=ast.Attribute(
                value=self.visit(node.value),
                attr='__sidewinder_getattribute__',
                ctx=ast.Load()
            ),
            args=[
                ast.Constant(value=node.attr),
                ast.Name(id='__sidewinder_state', ctx=ast.Load())
            ],
            keywords=[]
        )
    
    def visit_Subscript(self, node: ast.Subscript) -> Any:
        """
        Transform subscript operation.
        
        a[b] -> a.__sidewinder_getitem__(b, __sidewinder_state)
        """
        return ast.Call(
            func=ast.Attribute(
                value=self.visit(node.value),
                attr='__sidewinder_getitem__',
                ctx=ast.Load()
            ),
            args=[self.visit(node.slice), ast.Name(id='__sidewinder_state', ctx=ast.Load())],
            keywords=[]
        )
    
    def visit_Slice(self, node: ast.Slice) -> Any:
        """Transform slice - convert to slice object."""
        # a[1:5:2] -> slice(1, 5, 2)
        return ast.Call(
            func=ast.Name(id='slice', ctx=ast.Load()),
            args=[
                self.visit(node.lower) if node.lower else ast.Constant(value=None),
                self.visit(node.upper) if node.upper else ast.Constant(value=None),
                self.visit(node.step) if node.step else ast.Constant(value=None),
            ],
            keywords=[]
        )
    
    def visit_ListComp(self, node: ast.ListComp) -> Any:
        """
        Transform list comprehension to explicit loop.
        
        [x for x in items] ->
        __result = []
        for x in items:
            __result.append(x)
        """
        # TODO: Need to convert comprehension to statements
        # This requires returning multiple statements, which is tricky in expression context
        # For now, leave as-is
        self.generic_visit(node)
        return node
    
    def visit_DictComp(self, node: ast.DictComp) -> Any:
        """Transform dict comprehension to explicit loop."""
        # TODO: Similar to ListComp
        self.generic_visit(node)
        return node
    
    def visit_SetComp(self, node: ast.SetComp) -> Any:
        """Transform set comprehension to explicit loop."""
        # TODO: Similar to ListComp
        self.generic_visit(node)
        return node
    
    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        """Transform generator expression to generator function."""
        # TODO: Convert to explicit generator function
        self.generic_visit(node)
        return node
    
    def visit_Lambda(self, node: ast.Lambda) -> Any:
        """
        Transform lambda to include __sidewinder_state parameter.
        
        lambda x: x + 1 -> lambda x, __sidewinder_state: x.__sidewinder_add__(1, __sidewinder_state)
        """
        # Add state parameter
        has_kwargs = node.args.kwarg is not None
        state_param = self._make_sidewinder_state_param()
        
        if has_kwargs:
            node.args.kwonlyargs.append(state_param)
            if node.args.kw_defaults is None:
                node.args.kw_defaults = []
            node.args.kw_defaults.append(None)
        else:
            node.args.args.append(state_param)
        
        # Transform body
        node.body = self.visit(node.body)
        
        return node
    
    def visit_IfExp(self, node: ast.IfExp) -> Any:
        """Transform conditional expression (ternary operator)."""
        node.test = self.visit(node.test)
        node.body = self.visit(node.body)
        node.orelse = self.visit(node.orelse)
        return node
    
    def visit_Dict(self, node: ast.Dict) -> Any:
        """Transform dictionary literal."""
        node.keys = [self.visit(k) if k else None for k in node.keys]
        node.values = [self.visit(v) for v in node.values]
        return node
    
    def visit_Set(self, node: ast.Set) -> Any:
        """Transform set literal."""
        node.elts = [self.visit(elt) for elt in node.elts]
        return node
    
    def visit_List(self, node: ast.List) -> Any:
        """Transform list literal."""
        node.elts = [self.visit(elt) for elt in node.elts]
        return node
    
    def visit_Tuple(self, node: ast.Tuple) -> Any:
        """Transform tuple literal."""
        node.elts = [self.visit(elt) for elt in node.elts]
        return node
    
    def visit_Yield(self, node: ast.Yield) -> Any:
        """Transform yield expression."""
        if node.value:
            node.value = self.visit(node.value)
        return node
    
    def visit_YieldFrom(self, node: ast.YieldFrom) -> Any:
        """Transform yield from expression."""
        node.value = self.visit(node.value)
        return node
    
    def visit_Await(self, node: ast.Await) -> Any:
        """Transform await expression."""
        node.value = self.visit(node.value)
        return node
    
    def visit_FormattedValue(self, node: ast.FormattedValue) -> Any:
        """Transform formatted value in f-string."""
        node.value = self.visit(node.value)
        if node.format_spec:
            node.format_spec = self.visit(node.format_spec)
        return node
    
    def visit_JoinedStr(self, node: ast.JoinedStr) -> Any:
        """Transform f-string."""
        node.values = [self.visit(val) for val in node.values]
        return node
    
    def visit_Starred(self, node: ast.Starred) -> Any:
        """Transform starred expression."""
        node.value = self.visit(node.value)
        return node
    
    def visit_Name(self, node: ast.Name) -> Any:
        """Name nodes are unchanged."""
        return node
    
    def visit_Constant(self, node: ast.Constant) -> Any:
        """Constant nodes are unchanged."""
        return node
    
    def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
        """Transform named expression (walrus operator)."""
        node.target = self.visit(node.target)
        node.value = self.visit(node.value)
        return node
    
    # ========== Pattern Matching Nodes ==========
    
    def visit_match_case(self, node: ast.match_case) -> Any:
        """Transform match case."""
        node.pattern = self.visit(node.pattern)
        if node.guard:
            node.guard = self.visit(node.guard)
        node.body = [self.visit(stmt) for stmt in node.body]
        return node
    
    def visit_MatchValue(self, node: ast.MatchValue) -> Any:
        """Transform match value pattern."""
        node.value = self.visit(node.value)
        return node
    
    def visit_MatchSingleton(self, node: ast.MatchSingleton) -> Any:
        """Match singleton pattern is unchanged."""
        return node
    
    def visit_MatchSequence(self, node: ast.MatchSequence) -> Any:
        """Transform match sequence pattern."""
        node.patterns = [self.visit(p) for p in node.patterns]
        return node
    
    def visit_MatchMapping(self, node: ast.MatchMapping) -> Any:
        """Transform match mapping pattern."""
        node.keys = [self.visit(k) for k in node.keys]
        node.patterns = [self.visit(p) for p in node.patterns]
        if node.rest:
            # rest is just a name, doesn't need visiting
            pass
        return node
    
    def visit_MatchClass(self, node: ast.MatchClass) -> Any:
        """Transform match class pattern."""
        node.cls = self.visit(node.cls)
        node.patterns = [self.visit(p) for p in node.patterns]
        # kwd_patterns are just names
        return node
    
    def visit_MatchStar(self, node: ast.MatchStar) -> Any:
        """Match star pattern is unchanged."""
        return node
    
    def visit_MatchAs(self, node: ast.MatchAs) -> Any:
        """Transform match as pattern."""
        if node.pattern:
            node.pattern = self.visit(node.pattern)
        return node
    
    def visit_MatchOr(self, node: ast.MatchOr) -> Any:
        """Transform match or pattern."""
        node.patterns = [self.visit(p) for p in node.patterns]
        return node
    
    # ========== Type Parameter Nodes ==========
    
    def visit_TypeVar(self, node: ast.TypeVar) -> Any:
        """Transform type variable."""
        if node.bound:
            node.bound = self.visit(node.bound)
        return node
    
    def visit_ParamSpec(self, node: ast.ParamSpec) -> Any:
        """Transform parameter specification."""
        return node
    
    def visit_TypeVarTuple(self, node: ast.TypeVarTuple) -> Any:
        """Transform type variable tuple."""
        return node
    
    # ========== Helper/Supporting Nodes ==========
    
    def visit_comprehension(self, node: ast.comprehension) -> Any:
        """Transform comprehension clause."""
        node.target = self.visit(node.target)
        node.iter = self.visit(node.iter)
        node.ifs = [self.visit(cond) for cond in node.ifs]
        return node
    
    def visit_arguments(self, node: ast.arguments) -> Any:
        """Transform function arguments."""
        # Arguments are handled by FunctionDef/Lambda visitors
        return node
    
    def visit_arg(self, node: ast.arg) -> Any:
        """Transform function argument."""
        if node.annotation:
            node.annotation = self.visit(node.annotation)
        return node
    
    def visit_keyword(self, node: ast.keyword) -> Any:
        """Transform keyword argument."""
        node.value = self.visit(node.value)
        return node
    
    def visit_alias(self, node: ast.alias) -> Any:
        """Import alias is unchanged."""
        return node
    
    def visit_withitem(self, node: ast.withitem) -> Any:
        """Transform with item."""
        node.context_expr = self.visit(node.context_expr)
        if node.optional_vars:
            node.optional_vars = self.visit(node.optional_vars)
        return node


def transform_code(source_code: str) -> str:
    """
    Transform Python source code for Sidewinder symbolic execution.
    
    Args:
        source_code: Python source code as string
        
    Returns:
        Transformed Python source code as string
    """
    tree = ast.parse(source_code)
    transformer = SidewinderTransformer()
    transformed_tree = transformer.visit(tree)
    ast.fix_missing_locations(transformed_tree)
    return ast.unparse(transformed_tree)


if __name__ == "__main__":
    # Test the transformer
#     test_code = """
# def add(x, y):
#     return x + y

# def greet(name, **kwargs):
#     print(f"Hello {name}")

# result = add(1, 2)

# for i in range(10):
#     print(i)

    test_code = """
def foo(x, *k, **y):
    pass
"""

# a = [x * 2 for x in range(5)]
# """
    
    print("=== Original Code ===")
    print(test_code)
    print("\n=== Transformed Code ===")
    transformed_code = transform_code(test_code)
    print(transformed_code)
    exec(transformed_code)

       
