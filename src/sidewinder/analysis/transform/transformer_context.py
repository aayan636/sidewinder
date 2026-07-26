import ast
from typing import Optional, Tuple, List
from contextlib import contextmanager

class TransformerContext:
    """
    Manages the current AST node context during transformation.
    
    When transforming expressions that need to be broken into multiple statements
    (e.g., a.b.c → t1=a.b; t2=t1.c), the preamble statements need to be inserted
    into the nearest enclosing statement list.
    
    This tracks the current node AND which attribute (body, orelse, finalbody, etc.)
    we're currently building, so expression visitors know exactly where to append
    their preamble statements.
    """
    
    def __init__(self):
        # Stack of (node, attr_name) tuples
        # e.g., (If node, 'body') or (If node, 'orelse')
        self.context_stack: List[Tuple[ast.AST, str, list]] = []
    
    def push_context(self, node: ast.AST, attr_name: str) -> None:
        """
        Enter a new context for building a statement list.
        
        Args:
            node: The AST node containing the statement list
            attr_name: The attribute name (e.g., 'body', 'orelse', 'finalbody')
        """
        self.context_stack.append((node, attr_name, []))
    
    def pop_context(self) -> Tuple[ast.AST, str]:
        """Exit the current context."""
        if not self.context_stack:
            raise RuntimeError("Cannot pop_context: context stack is empty")
        # setattr(self.context_stack[-1][0], self.context_stack[-1][1], self.context_stack[-1][2])
        return self.context_stack.pop()[:-1]
    
    @contextmanager
    def enter_context(self, node: ast.AST, attr_name: str):
        """
        Context manager for entering/exiting a statement list context.
        
        Usage:
            with self.current_context.enter_context(if_node, 'body'):
                # transform statements, preambles go into if_node.body
                for stmt in node.body:
                    result = self.visit(stmt)
                    ...
        """
        self.push_context(node, attr_name)
        try:
            yield self
        finally:
            self.pop_context()
    
    def append_stmt(self, stmt: ast.stmt) -> None:
        """
        Append a statement to the current context's statement list.
        
        Expression visitors call this to add preamble statements.
        """
        if not self.context_stack:
            raise RuntimeError("No context available - cannot append statement")
        
        node, attr_name, stmt_list = self.context_stack[-1]
        
        if not hasattr(node, attr_name):
            raise RuntimeError(
                f"Node {type(node).__name__} has no attribute '{attr_name}'"
            )
                
        if not isinstance(getattr(node, attr_name), list):
            raise RuntimeError(
                f"Attribute {attr_name} of {type(node).__name__} is not a list"
            )
        
        stmt_list.append(stmt)