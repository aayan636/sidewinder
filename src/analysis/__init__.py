"""
Python Code Analysis Package

This package provides comprehensive Python code analysis capabilities.
"""

from .analyzer import PythonCodeAnalyzer
from .ast.transformer import SidewinderPythonASTTransformer

__all__ = ['PythonCodeAnalyzer', 'SidewinderPythonASTTransformer']
__version__ = '1.0.0' 