import ast
from typing import Any

from analysis.transform.errors import SidewinderIllegalStateError
from analysis.symbolic.hook import SidewinderHookNames
from analysis.transform.transformer_helpers import SidewinderTransformerHelpers

class SidewinderExprTransformerMixin(SidewinderTransformerHelpers):
    def visit_BinOp(self, node: ast.BinOp) -> tuple[list[ast.stmt], ast.expr]:
        """
        Transform binary operation to method call.
        
        a + b -> a.__add__(b, __sidewinder_state)
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
            return [], node
        
        method_name = f'__{op_name}__'
        
        return [], ast.Call(
            func=ast.Attribute(
                value=self._visit_expr(node.left),
                attr=method_name,
                ctx=ast.Load()
            ),
            args=[self._visit_expr(node.right), ast.Name(id='__sidewinder_state', ctx=ast.Load())],
            keywords=[]
        )
    
    def visit_UnaryOp(self, node: ast.UnaryOp) -> tuple[list[ast.stmt], ast.expr]:
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
            return [], node
        
        # Special case for 'not' - it's not a dunder method
        if op_name == 'not':
            # TODO: 'not x' should become something like: not x.__sidewinder_bool__(__sidewinder_state)
            # For now, just transform the operand
            return [], ast.UnaryOp(op=node.op, operand=self._visit_expr(node.operand))
        
        method_name = f'__sidewinder_{op_name}__'
        
        return [], ast.Call(
            func=ast.Attribute(
                value=self._visit_expr(node.operand),
                attr=method_name,
                ctx=ast.Load()
            ),
            args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
            keywords=[]
        )
    
    def visit_BoolOp(self, node: ast.BoolOp) -> tuple[list[ast.stmt], ast.expr]:
        """
        Transform boolean operation.
        
        a and b -> short-circuit evaluation with __sidewinder_bool__
        a or b -> short-circuit evaluation with __sidewinder_bool__
        """
        raise NotImplementedError("Bool Op not yet supported")
    
    def visit_Compare(self, node: ast.Compare) -> tuple[list[ast.stmt], ast.expr]:
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
            comparator = node.comparators[0]
            
            if op_name in ['is', 'is_not']:
                # 'is' and 'is not' are identity checks, not method calls
                # Transform operands but keep the operator
                node.left = self._visit_expr(node.left)
                node.comparators = [self._visit_expr(comparator)]
                return [], node
            
            if op_name in ['contains', 'not_contains']:
                # 'in' is reversed: a in b -> b.__contains__(a)
                method_name = "__contains__"
                result = ast.Call(
                    func=ast.Attribute(
                        value=self._visit_expr(comparator),
                        attr=method_name,
                        ctx=ast.Load()
                    ),
                    args=[self._visit_expr(node.left)],
                    keywords=[self._sidewinder_state_keyword()],
                )
                
                if op_name == 'not_contains':
                    # Negate the result
                    result = ast.UnaryOp(op=ast.Not(), operand=result)
                
                return [], result
            
            if op_name:
                method_name = f'__{op_name}__'
                return [], ast.Call(
                    func=ast.Attribute(
                        value=self._visit_expr(node.left),
                        attr=method_name,
                        ctx=ast.Load()
                    ),
                    args=[self._visit_expr(comparator)],
                    keywords=[self._sidewinder_state_keyword()],
                )
            else:
                raise SidewinderIllegalStateError("Expected an operator")
        else:
            raise NotImplementedError("Chained Operators are not yet supported")
        
        # Multiple comparisons - transform each operand
        node.left = self.visit(node.left)
        node.comparators = [self.visit(comp) for comp in node.comparators]
        return node
    
    def visit_Call(self, node: ast.Call) -> tuple[list[ast.stmt], ast.expr]:
        """
        Transform function call to include __sidewinder_state.
        
        func(a, b) -> func(a, b, __sidewinder_state=__sidewinder_state)
        func(a, x=b) -> func(a, __sidewinder_state=__sidewinder_state, x=b) [if func has **kwargs]
        """
        # Transform the function expression
        
        transformed_func = self._visit_expr(node.func)
        
        # Transform arguments
        transformed_args = [self._visit_expr(arg) for arg in node.args]
        transformed_keywords = [ast.keyword(kw.arg, self._visit_expr(kw.value)) for kw in node.keywords]

        transformed_keywords.insert(0, self._sidewinder_state_keyword())
        
        return [], ast.Call(
            func=transformed_func,
            args=transformed_args,
            keywords=transformed_keywords,
            lineno=node.lineno,
            col_offset=node.col_offset,
            end_lineno=node.end_lineno,
            end_col_offset=node.end_col_offset
        )
    
    def visit_Attribute(self, node: ast.Attribute) -> tuple[list[ast.stmt], ast.expr]:
        """
        Transform attribute access to sidewinder getattr hook.
        
        a.b -> 
        __t1 = a.__sidewinder_getattr__("b", __sidewinder_state__=__sidewinder_state__)
        
        For chained access a.b.c, recursion handles it:
        __t1 = a.__sidewinder_getattr__("b", __sidewinder_state__=__sidewinder_state__)
        __t2 = __t1.__sidewinder_getattr__("c", __sidewinder_state__=__sidewinder_state__)
        """
        # recursively transform the object being accessed
        visited_obj = self._visit_expr(node.value)

        # store result in temp
        temp = self._fresh_temp("__sidewinder_attr")
        stmt = ast.Assign(
            targets=[ast.Name(id=temp, ctx=ast.Store())],
            value=self._emit_method_hook_call(
                visited_obj,
                SidewinderHookNames.SIDEWINDER_GETATTR,
                ast.Constant(value=node.attr),
            ),
            lineno=0, col_offset=0,
        )

        return [stmt], ast.Name(id=temp, ctx=ast.Load())
    
    def visit_Subscript(self, node: ast.Subscript) -> tuple[list[ast.stmt], ast.expr]:
        """
        Transform subscript operation.

        a[b] ->
        __t1 = a.__sidewinder_getitem__(b,__sidewinder_state__=__sidewinder_state__)
        """
        visited_obj = self._visit_expr(node.value)
        visited_slice = self._visit_expr(node.slice)

        temp = self._fresh_temp("__sidewinder_subscript")

        stmt = ast.Assign(
            targets=[ast.Name(id=temp, ctx=ast.Store())],
            value=self._emit_method_hook_call(
                visited_obj,
                SidewinderHookNames.SIDEWINDER_GETITEM,
                visited_slice,
            ),
            lineno=0,
            col_offset=0,
        )

        return [stmt], ast.Name(id=temp, ctx=ast.Load())
    
    def visit_Slice(self, node: ast.Slice) -> Any:
        """Transform slice - convert to slice object."""
        # a[1:5:2] -> slice(1, 5, 2)
        return [], ast.Call(
            func=ast.Name(id='slice', ctx=ast.Load()),
            args=[
                self._visit_expr(node.lower) if node.lower else ast.Constant(value=None),
                self._visit_expr(node.upper) if node.upper else ast.Constant(value=None),
                self._visit_expr(node.step) if node.step else ast.Constant(value=None),
            ],
            keywords=[]
        )
    
    def visit_ListComp(self, node: ast.ListComp) -> tuple[list[ast.stmt], ast.expr]:
        """
        [expr for x in xs if pred]

        ->
        __result = []
        for x in xs:
            if pred:
                __result.append(expr)

        return __result
        """
        result_name = self._fresh_temp("__sidewinder_listcomp")

        init_stmt = ast.Assign(
            targets=[ast.Name(id=result_name, ctx=ast.Store())],
            value=ast.List(elts=[], ctx=ast.Load()),
            lineno=0,
            col_offset=0,
        )

        append_stmt = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=result_name, ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
                args=[node.elt],
                keywords=[],
            ),
            lineno=0,
            col_offset=0,
        )

        body: list[ast.stmt] = [append_stmt]

        #
        # Build nested fors/ifs from inside out.
        #
        for gen in reversed(node.generators):
            current_body: list[ast.stmt] = body

            for if_expr in reversed(gen.ifs):
                current_body = [
                    ast.If(
                        test=if_expr,
                        body=current_body,
                        orelse=[],
                        lineno=0,
                        col_offset=0,
                    )
                ]

            body = [
                ast.For(
                    target=gen.target,
                    iter=gen.iter,
                    body=current_body,
                    orelse=[],
                    lineno=0,
                    col_offset=0,
                )
            ]

        stmts: list[ast.stmt] = [init_stmt] + body

        # Now run the generated code through the normal transformer, and return the result
        return self._visit_list_of_stmts(stmts), ast.Name(id=result_name, ctx=ast.Load())
        
    def visit_DictComp(self, node: ast.DictComp) -> Any:
        """Transform dict comprehension to explicit loop."""
        raise NotImplementedError("DictComp not supported yet.")
    
    def visit_SetComp(self, node: ast.SetComp) -> Any:
        """Transform set comprehension to explicit loop."""
        raise NotImplementedError("SetComp not supported yet.")
    
    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        """Transform generator expression to generator function."""
        raise NotImplementedError("GeneratorExp not supported yet.")
    
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
        node.body = self._visit_expr(node.body)
        
        return [], node
    
    def visit_IfExp(self, node: ast.IfExp) -> tuple[list[ast.stmt], ast.expr]:
        result = self._fresh_temp("__sidewinder_ifexp")

        init = ast.Assign(
            targets=[ast.Name(id=result, ctx=ast.Store())],
            value=ast.Constant(value=None),
            lineno=0,
            col_offset=0,
        )

        assign_body = ast.Assign(
            targets=[ast.Name(id=result, ctx=ast.Store())],
            value=node.body,
            lineno=0,
            col_offset=0,
        )

        assign_orelse = ast.Assign(
            targets=[ast.Name(id=result, ctx=ast.Store())],
            value=node.orelse,
            lineno=0,
            col_offset=0,
        )

        if_stmt = ast.If(
            test=node.test,
            body=[assign_body],
            orelse=[assign_orelse],
            lineno=0,
            col_offset=0,
        )

        stmts = [init, if_stmt]

        # Process the simplified expression through transformer
        return self._visit_list_of_stmts(stmts), ast.Name(id=result, ctx=ast.Load())
    
    def visit_Dict(self, node: ast.Dict) -> Any:
        """Transform dictionary literal."""
        assert (k is not None for k in node.keys), "Unpacking dict is not supported yet"
        node.keys = [self._visit_expr(k) if k else None for k in node.keys]
        node.values = [self._visit_expr(v) for v in node.values]
        return [], node
    
    def visit_Set(self, node: ast.Set) -> Any:
        """Transform set literal."""
        node.elts = [self._visit_expr(elt) for elt in node.elts]
        return [], node
    
    def visit_List(self, node: ast.List) -> Any:
        """Transform list literal."""
        node.elts = [self._visit_expr(elt) for elt in node.elts]
        return [], node
    
    def visit_Tuple(self, node: ast.Tuple) -> Any:
        """Transform tuple literal."""
        node.elts = [self._visit_expr(elt) for elt in node.elts]
        return [], node
    
    def visit_Await(self, node: ast.Await) -> Any:
        """Transform await expression."""
        raise NotImplementedError("Generators are not supported yet")
    
    def visit_FormattedValue(self, node: ast.FormattedValue) -> Any:
        """Transform formatted value in f-string."""
        node.value = self._visit_expr(node.value)
        if node.format_spec:
            node.format_spec = self._visit_expr(node.format_spec)
        return [], node
    
    def visit_JoinedStr(self, node: ast.JoinedStr) -> Any:
        """Transform f-string."""
        node.values = [self._visit_expr(val) for val in node.values]
        return [], node
    
    def visit_Starred(self, node: ast.Starred) -> Any:
        """Transform starred expression."""
        node.value = self._visit_expr(node.value)
        return [], node
    
    def visit_Name(self, node: ast.Name) -> Any:
        """Name nodes are unchanged."""
        return [], node
    
    def visit_Constant(self, node: ast.Constant) -> Any:
        """Constant nodes are unchanged."""
        return [], node
    
    def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
        """Transform named expression (walrus operator)."""
        raise NotImplementedError("NamedExpr := not implemented yet.")
