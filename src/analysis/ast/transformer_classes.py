import ast
from typing import Any

from analysis.ast.transformer_helpers import SidewinderTransformerHelpers

class SidewinderClassTransformerMixin(SidewinderTransformerHelpers):
    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        """Visit a class definition - transform all methods."""
        self.current_scope.append(node.name)
        
        # Transform class body
        with self.current_context.enter_context(node, "body") as c:
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