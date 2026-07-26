import ast

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers

class SidewinderWithTransformerMixin(SidewinderTransformerHelpers):
    def visit_With(self, node: ast.With) -> list[ast.stmt]:
        """
        Normalize a `with` statement into simpler AST constructs before the
        Sidewinder lowering pass.

        TODO(sidewinder): This is a simplified desugaring and does NOT exactly
        match Python's context manager semantics.

        In particular:
        - __exit__ is not passed exception information.
        - Exception suppression is not modeled.
        - The exact protocol defined by the language reference is intentionally
        simplified.

        Multiple context managers are recursively desugared.
        """
        return self._transform_with(
            node.items,
            node.body,
            node.lineno,
            node.col_offset,
            is_async=False,
        )


    def visit_AsyncWith(self, node: ast.AsyncWith) -> list[ast.stmt]:
        """See visit_With()."""
        return self._transform_with(
            node.items,
            node.body,
            node.lineno,
            node.col_offset,
            is_async=True,
        )


    def _transform_with(
        self,
        items: list[ast.withitem],
        body: list[ast.stmt],
        lineno: int,
        col_offset: int,
        is_async: bool,
    ) -> list[ast.stmt]:
        # Desugar multiple context managers recursively.
        if len(items) > 1:
            inner = (
                ast.AsyncWith(
                    items=items[1:],
                    body=body,
                    lineno=lineno,
                    col_offset=col_offset,
                )
                if is_async
                else ast.With(
                    items=items[1:],
                    body=body,
                    lineno=lineno,
                    col_offset=col_offset,
                )
            )
            return self._transform_with(
                [items[0]],
                [inner],
                lineno,
                col_offset,
                is_async,
            )

        item = items[0]
        mgr_name = self._fresh_temp("__mgr")

        # __mgr = expr
        mgr_assign = ast.Assign(
            targets=[ast.Name(id=mgr_name, ctx=ast.Store())],
            value=item.context_expr,
            lineno=lineno,
            col_offset=col_offset,
        )

        enter_name = "__enter__" if not is_async else "__aenter__"
        exit_name = "__exit__" if not is_async else "__aexit__"

        enter_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=mgr_name, ctx=ast.Load()),
                attr=enter_name,
                ctx=ast.Load(),
            ),
            args=[],
            keywords=[],
        )

        enter_value: ast.expr = (
            ast.Await(value=enter_call) if is_async else enter_call
        )

        try_body: list[ast.stmt] = []

        if item.optional_vars is not None:
            try_body.append(
                ast.Assign(
                    targets=[item.optional_vars],
                    value=enter_value,
                    lineno=lineno,
                    col_offset=col_offset,
                )
            )
        else:
            try_body.append(
                ast.Expr(
                    value=enter_value,
                    lineno=lineno,
                    col_offset=col_offset,
                )
            )

        try_body.extend(body)

        exit_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=mgr_name, ctx=ast.Load()),
                attr=exit_name,
                ctx=ast.Load(),
            ),
            args=[],
            keywords=[],
        )

        exit_expr: ast.expr = (
            ast.Await(value=exit_call) if is_async else exit_call
        )

        try_stmt = ast.Try(
            body=try_body,
            handlers=[],
            orelse=[],
            finalbody=[
                ast.Expr(
                    value=exit_expr,
                    lineno=lineno,
                    col_offset=col_offset,
                )
            ],
            lineno=lineno,
            col_offset=col_offset,
        )

        # Push the normalized AST back through the transformer.
        return self._visit_list_of_stmts([mgr_assign, try_stmt])