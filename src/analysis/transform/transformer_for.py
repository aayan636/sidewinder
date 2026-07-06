import ast

from analysis.transform.transformer_helpers import SidewinderTransformerHelpers

class SidewinderForTransformerMixin(SidewinderTransformerHelpers):
    def visit_For(self, node: ast.For) -> list[ast.stmt]:
        """
        Transform for loop to explicit iterator protocol.
        
        for item in iterable:
            body
        
        Becomes:
        _iter = iterable.__sidewinder_iter__(__sidewinder_state)
        while True:
            try:
                _next_val = _iter.__sidewinder_next__(__sidewinder_state)
                item = _next_val  # via _visit_target, handles tuple unpack etc.
                body
            except StopIteration:
                break
        """
        if node.orelse:
            raise NotImplementedError("for/else not supported")
        return self._transform_for(node.iter, node.target, node.body, is_async=False)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> list[ast.stmt]:
        """
        Transform async for loop to explicit async iterator protocol.
        
        async for item in iterable:
            body
        
        Becomes:
        _aiter = iterable.__sidewinder_aiter__(__sidewinder_state)
        while True:
            try:
                _next_val = await _aiter.__sidewinder_anext__(__sidewinder_state)
                item = _next_val  # via _visit_target, handles tuple unpack etc.
                body
            except StopAsyncIteration:
                break
        """
        if node.orelse:
            raise NotImplementedError("async for/else not supported")
        return self._transform_for(node.iter, node.target, node.body, is_async=True)
    
    def _transform_for(
        self,
        iter_expr: ast.expr,
        target: ast.expr,
        body: list[ast.stmt],
        is_async: bool,
    ) -> list[ast.stmt]:
        iter_method  = '__sidewinder_aiter__' if is_async else '__sidewinder_iter__'
        next_method  = '__sidewinder_anext__' if is_async else '__sidewinder_next__'
        stop_exc     = 'StopAsyncIteration'   if is_async else 'StopIteration'
        iter_tmp     = self._fresh_temp("__aiter" if is_async else "__iter")

        # _iter = iterable.__sidewinder_iter__(__sidewinder_state)
        iter_assign = ast.Assign(
            targets=[ast.Name(id=iter_tmp, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=self._visit_expr(iter_expr),
                    attr=iter_method,
                    ctx=ast.Load(),
                ),
                args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
                keywords=[],
            ),
            lineno=0, col_offset=0,
        )

        # _next_val = _iter.__sidewinder_next__(__sidewinder_state)
        # (possibly wrapped in await)
        next_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=iter_tmp, ctx=ast.Load()),
                attr=next_method,
                ctx=ast.Load(),
            ),
            args=[ast.Name(id='__sidewinder_state', ctx=ast.Load())],
            keywords=[],
        )
        next_value = ast.Await(value=next_call) if is_async else next_call    
        # emit next call into a fresh tmp, then assign to target via _visit_target
        next_tmp = self._fresh_temp("__next_val")
        next_assign = ast.Assign(
            targets=[ast.Name(id=next_tmp, ctx=ast.Store())],
            value=next_value,
            lineno=0, col_offset=0,
        )   

        # Create empty try block to push statements into
        try_block = ast.Try(
            body=[next_assign],
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id=stop_exc, ctx=ast.Load()),
                    name=None,
                    body=[ast.Break()],
                )
            ],
            orelse=[],
            finalbody=[],
        )

        # transform loop body
        with self.current_context.enter_context(try_block, "body"): 
            # assign tmp to actual target (handles tuple unpack, attribute, subscript etc.)
            self._visit_target(target, ast.Name(id=next_tmp, ctx=ast.Load()))
            transformed_body = self._visit_list_of_stmts(body)

        try_block.body.extend(transformed_body)

        while_loop = ast.While(
            test=ast.Constant(value=True),
            body=[try_block],
            orelse=[],
            lineno=0, col_offset=0,
        )

        return [iter_assign, while_loop]