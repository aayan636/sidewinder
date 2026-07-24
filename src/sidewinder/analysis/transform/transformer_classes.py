import ast
from typing import Any

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers

class SidewinderClassTransformerMixin(SidewinderTransformerHelpers):
    def visit_ClassDef(self, node: ast.ClassDef) -> list[ast.stmt]:
        """Visit a class definition - transform all methods."""
        self.current_scope.append(node.name)

        # Transform class body
        with self.current_context.enter_context(node, "body"):
            node.body = self._visit_list_of_stmts(node.body)

        # Transform bases
        new_bases = []
        new_bases_stmts: list[ast.stmt] = []
        for base in node.bases:
            lowered = self._visit_expr(base)
            # TODO: handle base expression stmts if needed
            new_bases.append(lowered.expr)
            new_bases_stmts.extend(lowered.stmts)

        node.bases = new_bases

        # Transform keywords
        for kw in node.keywords:
            lowered = self._visit_expr(kw.value)
            # TODO: handle keyword expression stmts if needed
            kw.value = lowered.expr

        self.current_scope.pop()

        # Lower decorators
        decorator_pre, decorator_post = self._transform_decorators(node)

        ret: list[ast.stmt] = []
        ret.extend(new_bases_stmts)
        
        ret.extend(decorator_pre)

        # Emit class definition
        ret.append(node)

        # Apply decorators after class exists
        decorator_transforms = self._visit_list_of_stmts(decorator_post)
        ret.extend(decorator_transforms)

        return ret