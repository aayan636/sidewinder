import ast

from analysis.transform.transformer_helpers import SidewinderTransformerHelpers

class SidewinderWithTransformerMixin(SidewinderTransformerHelpers):
    def visit_With(self, node: ast.With) -> list[ast.stmt]:
        """
        Transform with statement to explicit __enter__/__exit__ calls.
        
        with expr as var:
            body
        
        Becomes:
        __ctx = expr.__sidewinder_enter__(__sidewinder_state)
        try:
            var = __ctx
            body
        finally:
            __ctx.__sidewinder_exit__(__sidewinder_state)

        Multiple context managers are desugared recursively:
        with a as x, b as y:
            body
        
        Becomes:
        with a as x:
            with b as y:
                body
        """
        return self._transform_with(node.items, node.body, node.lineno, node.col_offset, is_async=False)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> list[ast.stmt]:
        """
        Transform async with statement to explicit __aenter__/__aexit__ calls.
        
        async with expr as var:
            body
        
        Becomes:
        __ctx = await expr.__sidewinder_aenter__(__sidewinder_state)
        try:
            var = __ctx
            body
        finally:
            await __ctx.__sidewinder_aexit__(__sidewinder_state)
        """
        return self._transform_with(node.items, node.body, node.lineno, node.col_offset, is_async=True)

    def _transform_with(
        self,
        items: list[ast.withitem],
        body: list[ast.stmt],
        lineno: int,
        col_offset: int,
        is_async: bool,
    ) -> list[ast.stmt]:

        if len(items) > 1:
            inner = ast.With(
                items=items[1:],
                body=body,
                lineno=lineno, col_offset=col_offset,
            ) if not is_async else ast.AsyncWith(
                items=items[1:],
                body=body,
                lineno=lineno, col_offset=col_offset,
            )
            # Extract the first context variable, and the constructed with the reamining variables processed separately
            return self._transform_with([items[0]], [inner], lineno, col_offset, is_async)
        
        enter_method = '__sidewinder_aenter__' if is_async else '__sidewinder_enter__'
        exit_method  = '__sidewinder_aexit__'  if is_async else '__sidewinder_exit__'

        item = items[0]
        ctx_tmp = self._fresh_temp("__ctx")

        enter_call = ast.Call(
            func=ast.Attribute(
                value=self._visit_expr(item.context_expr),
                attr=enter_method,
                ctx=ast.Load(),
            ),
            args=[],
            keywords=[ast.keyword(arg='__sidewinder_state', value=ast.Name(id='__sidewinder_state', ctx=ast.Load()))],
        )

        # __ctx = await expr.__sidewinder_aenter__(...) or expr.__sidewinder_enter__(...)
        ctx_assign = ast.Assign(
            targets=[ast.Name(id=ctx_tmp, ctx=ast.Store())],
            value=ast.Await(value=enter_call) if is_async else enter_call,
            lineno=0, col_offset=0,
        )

        try_block = ast.Try(
            body=[],
            handlers=[],
            orelse=[],
            finalbody=[],
        )

        with self.current_context.enter_context(try_block, "body"):
            if item.optional_vars is not None:
                self._visit_target(
                    item.optional_vars,
                    ast.Name(id=ctx_tmp, ctx=ast.Load()),
                )
            transformed_body = self._visit_list_of_stmts(body)

        try_block.body.extend(transformed_body)

        exit_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=ctx_tmp, ctx=ast.Load()),
                attr=exit_method,
                ctx=ast.Load(),
            ),
            args=[],
            keywords=[ast.keyword(arg='__sidewinder_state', value=ast.Name(id='__sidewinder_state', ctx=ast.Load()))],
        )

        # In the transformed version we will only have a single name being used to call the __exit__ method (roughly __ctx.__exit__(....) so this should work)
        try_block.finalbody = [ast.Expr(
            value=ast.Await(value=exit_call) if is_async else exit_call,
            lineno=0, col_offset=0,
        )]

        return [ctx_assign, try_block]
