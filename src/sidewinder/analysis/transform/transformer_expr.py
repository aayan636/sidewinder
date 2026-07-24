import ast
from typing import Any

from sidewinder.analysis.transform.errors import SidewinderIllegalStateError
from sidewinder.analysis.symbolic.hook import SidewinderHookNames
from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers

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

        lowered_left = self._visit_expr(node.left)
        lowered_right = self._visit_expr(node.right)
        
        return lowered_left.stmts + lowered_right.stmts, ast.Call(
            func=ast.Attribute(
                value=lowered_left.expr,
                attr=method_name,
                ctx=ast.Load()
            ),
            args=[lowered_right.expr, ast.Name(id='__sidewinder_state', ctx=ast.Load())],
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
            lowered_operand = self._visit_expr(node.operand)
            return lowered_operand.stmts, ast.UnaryOp(op=node.op, operand=lowered_operand.expr)
        
        method_name = f'__sidewinder_{op_name}__'

        lowered_operand = self._visit_expr(node.operand)
        return lowered_operand.stmts, ast.Call(
            func=ast.Attribute(
                value=lowered_operand.expr,
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
                lowered_left = self._visit_expr(node.left)
                lowered_comparator = self._visit_expr(comparator)
                node.left = lowered_left.expr
                node.comparators = [lowered_comparator.expr]
                return lowered_left.stmts + lowered_comparator.stmts, node
            
            if op_name in ['contains', 'not_contains']:
                # 'in' is reversed: a in b -> b.__contains__(a)
                method_name = "__contains__"
                lowered_left = self._visit_expr(node.left)
                lowered_comparator = self._visit_expr(comparator)
                result = ast.Call(
                    func=ast.Attribute(
                        value=lowered_comparator.expr,
                        attr=method_name,
                        ctx=ast.Load()
                    ),
                    args=[lowered_left.expr],
                    keywords=[self._sidewinder_state_keyword()],
                )
                
                if op_name == 'not_contains':
                    # Negate the result
                    result = ast.UnaryOp(op=ast.Not(), operand=result)
                
                return lowered_left.stmts + lowered_comparator.stmts, result
            
            if op_name:
                method_name = f'__{op_name}__'
                lowered_left = self._visit_expr(node.left)
                lowered_comparator = self._visit_expr(comparator)
                return lowered_left.stmts + lowered_comparator.stmts, ast.Call(
                    func=ast.Attribute(
                        value=lowered_left.expr,
                        attr=method_name,
                        ctx=ast.Load()
                    ),
                    args=[lowered_comparator.expr],
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
        context_stmts = []
        
        lowered_func = self._visit_expr(node.func)
        context_stmts.extend(lowered_func.stmts)
        
        # Transform arguments
        transformed_args = []
        for arg in node.args:
            lowered_arg = self._visit_expr(arg)
            transformed_args.append(lowered_arg.expr)
            context_stmts.extend(lowered_arg.stmts)

        transformed_keywords = []
        for kw in node.keywords:
            lowered_kw_value = self._visit_expr(kw.value)
            transformed_keywords.append(ast.keyword(kw.arg, lowered_kw_value.expr))
            context_stmts.extend(lowered_kw_value.stmts)

        transformed_keywords.insert(0, self._sidewinder_state_keyword())
        
        return context_stmts, ast.Call(
            func=lowered_func.expr,
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
        lowered_visited_obj = self._visit_expr(node.value)

        # store result in temp
        temp = self._fresh_temp("__sidewinder_attr")
        stmt = ast.Assign(
            targets=[ast.Name(id=temp, ctx=ast.Store())],
            value=self._emit_method_hook_call(
                lowered_visited_obj.expr,
                SidewinderHookNames.SIDEWINDER_GETATTR,
                ast.Constant(value=node.attr),
            ),
            lineno=0, col_offset=0,
        )

        return lowered_visited_obj.stmts + [stmt], ast.Name(id=temp, ctx=ast.Load())
    
    def visit_Subscript(self, node: ast.Subscript) -> tuple[list[ast.stmt], ast.expr]:
        """
        Transform subscript operation.

        a[b] ->
        __t1 = a.__sidewinder_getitem__(b,__sidewinder_state__=__sidewinder_state__)
        """
        lowered_visited_obj = self._visit_expr(node.value)
        lowered_visited_slice = self._visit_expr(node.slice)

        temp = self._fresh_temp("__sidewinder_subscript")

        stmt = ast.Assign(
            targets=[ast.Name(id=temp, ctx=ast.Store())],
            value=self._emit_method_hook_call(
                lowered_visited_obj.expr,
                SidewinderHookNames.SIDEWINDER_GETITEM,
                lowered_visited_slice.expr,
            ),
            lineno=0,
            col_offset=0,
        )

        return lowered_visited_obj.stmts + lowered_visited_slice.stmts + [stmt], ast.Name(id=temp, ctx=ast.Load())
    
    def visit_Slice(self, node: ast.Slice) -> Any:
        """Transform slice - convert to slice object."""
        # a[1:5:2] -> slice(1, 5, 2)
        lowered_lower = self._visit_expr(node.lower) if node.lower else None
        lowered_upper = self._visit_expr(node.upper) if node.upper else None
        lowered_step = self._visit_expr(node.step) if node.step else None
        args = []
        args.append(lowered_lower.expr if lowered_lower else ast.Constant(value=None))
        args.append(lowered_upper.expr if lowered_upper else ast.Constant(value=None))
        args.append(lowered_step.expr if lowered_step else ast.Constant(value=None))

        context_stmts = []
        context_stmts.extend(lowered_lower.stmts) if lowered_lower else None
        context_stmts.extend(lowered_upper.stmts) if lowered_upper else None
        context_stmts.extend(lowered_step.stmts) if lowered_step else None

        return context_stmts, ast.Call(
            func=ast.Name(id='slice', ctx=ast.Load()),
            args=args,
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
        lowered_body = self._visit_expr(node.body)
        node.body = lowered_body.expr
        
        return lowered_body.stmts, node
    
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
        stmts = []
        new_keys = []
        new_values = []

        for key, value in zip(node.keys, node.values):
            if key is None:
                raise NotImplementedError("Dict unpacking not supported")

            lowered = self._visit_expr(key)
            stmts.extend(lowered.stmts)
            new_keys.append(lowered.expr)

            lowered = self._visit_expr(value)
            stmts.extend(lowered.stmts)
            new_values.append(lowered.expr)

        node.keys = new_keys
        node.values = new_values

        return stmts, node
    
    def visit_Set(self, node: ast.Set) -> Any:
        """Transform set literal."""
        stmts = []
        new_elts = []

        for elt in node.elts:
            lowered = self._visit_expr(elt)
            stmts.extend(lowered.stmts)
            new_elts.append(lowered.expr)

        node.elts = new_elts

        return stmts, node
    
    def visit_List(self, node: ast.List) -> Any:
        """Transform list literal."""
        stmts = []
        new_elts = []

        for elt in node.elts:
            lowered = self._visit_expr(elt)
            stmts.extend(lowered.stmts)
            new_elts.append(lowered.expr)

        node.elts = new_elts

        return stmts, node
    
    def visit_Tuple(self, node: ast.Tuple) -> Any:
        """Transform tuple literal."""
        stmts = []
        new_elts = []

        for elt in node.elts:
            lowered = self._visit_expr(elt)
            stmts.extend(lowered.stmts)
            new_elts.append(lowered.expr)

        node.elts = new_elts

        return stmts, node
    
    def visit_Await(self, node: ast.Await) -> Any:
        """Transform await expression."""
        raise NotImplementedError("Generators are not supported yet")
    
    def visit_FormattedValue(self, node: ast.FormattedValue) -> Any:
        """Transform formatted value in f-string."""
        stmts = []

        lowered = self._visit_expr(node.value)
        stmts.extend(lowered.stmts)
        node.value = lowered.expr

        if node.format_spec:
            lowered = self._visit_expr(node.format_spec)
            stmts.extend(lowered.stmts)
            node.format_spec = lowered.expr

        return stmts, node
    
    def visit_JoinedStr(self, node: ast.JoinedStr) -> Any:
        """Transform f-string."""
        stmts = []
        new_values = []

        for value in node.values:
            lowered = self._visit_expr(value)
            stmts.extend(lowered.stmts)
            new_values.append(lowered.expr)

        node.values = new_values

        return stmts, node
    
    def visit_Starred(self, node: ast.Starred) -> Any:
        """Transform starred expression."""
        stmts = []

        lowered = self._visit_expr(node.value)
        stmts.extend(lowered.stmts)
        node.value = lowered.expr

        return stmts, node
    
    def visit_Name(self, node: ast.Name) -> Any:
        """Name nodes are unchanged."""
        return [], node
    
    def visit_Constant(self, node: ast.Constant) -> Any:
        """Constant nodes are unchanged."""
        return [], node
    
    def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
        """Transform named expression (walrus operator)."""
        raise NotImplementedError("NamedExpr := not implemented yet.")
