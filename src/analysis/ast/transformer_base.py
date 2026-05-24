import ast
from typing import TypeVar, TypeAlias

from analysis.ast.transformer_context import TransformerContext

class SidewinderTransformerBase(ast.NodeTransformer):
    def generic_visit(self, node: ast.AST) -> None:
        raise NotImplementedError("All visitor methods must be implemented and not delegated to generic_visit of ast.NodeTransformer")

    def __init__(self):
        # Track which functions have **kwargs in their signature
        self.function_signatures: dict[str, bool] = {}  # name -> has_kwargs
        
        # Counter for generating fresh temporary variable names
        self.temp_counter = 0
        
        # Track current scope for variable naming
        self.current_scope = []

        # Current node where we append extra computation required
        self.current_context = TransformerContext()

T = TypeVar('T', bound=ast.expr)
