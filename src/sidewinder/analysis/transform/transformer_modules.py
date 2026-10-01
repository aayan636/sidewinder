import ast
from typing import Any

from sidewinder.analysis.transform.transformer_helpers import SidewinderTransformerHelpers

class SidewinderModuleTransformerMixin(SidewinderTransformerHelpers):
    def visit_Module(self, node: ast.Module) -> Any:
        """Visit a module node - add import for SidewinderState."""
        
        # Transform all statements in the module
        with self.current_context.enter_context(node, "body") as c:
            node.body = self._visit_list_of_stmts(node.body)
        return node