"""
Python Code Analyzer Module

This module provides comprehensive analysis capabilities for Python code files
using the PythonASTAnalyzerVisitor.
"""

import ast
from typing import Dict, List, Any, Optional
from analysis.transform.transformer import SidewinderTransformer


class PythonCodeAnalyzer:
    """A comprehensive analyzer for Python code files."""
    
    def __init__(self):
        self.visitor = SidewinderTransformer()
    
    def analyze_file(self, file_path: str):
        """
        Analyze a Python file and return analysis results.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            return self.analyze_code(content, file_path)
        except FileNotFoundError:
            return {"error": f"File not found: {file_path}"}
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}
    
    def analyze_code(self, code: str, file_name: str = "unknown"):
        """
        Analyze Python code string and return analysis results.
        
        Args:
            code: Python code as string
            file_name: Name of the file being analyzed
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        # try:
        #     tree = ast.parse(code)
            
        #     # Use the visitor to analyze the AST
        #     analysis = self.visitor.visit(tree)
            
    #         # Add file metadata
    #         analysis["file_name"] = file_name
    #         analysis["total_lines"] = len(code.splitlines())
    #         analysis["has_main_guard"] = any(
    #             const.get("type") == "main_guard" 
    #             for const in analysis.get("constants", [])
    #         )
            
    #         # Calculate summary statistics
    #         analysis["summary"] = {
    #             "total_functions": len(analysis.get("functions", [])) + len(analysis.get("async_functions", [])),
    #             "total_classes": len(analysis.get("classes", [])),
    #             "total_imports": len(analysis.get("imports", [])) + len(analysis.get("from_imports", [])),
    #             "total_variables": len(analysis.get("variables", [])),
    #             "total_type_annotations": len(analysis.get("type_annotations", [])),
    #             "total_control_flow": (
    #                 len(analysis.get("if_statements", [])) +
    #                 len(analysis.get("for_loops", [])) +
    #                 len(analysis.get("while_loops", [])) +
    #                 len(analysis.get("try_blocks", []))
    #             ),
    #             "total_expressions": (
    #                 len(analysis.get("call_expressions", [])) +
    #                 len(analysis.get("binary_operations", [])) +
    #                 len(analysis.get("unary_operations", [])) +
    #                 len(analysis.get("comparison_operations", []))
    #             ),
    #             "total_comprehensions": (
    #                 len(analysis.get("list_comprehensions", [])) +
    #                 len(analysis.get("dict_comprehensions", [])) +
    #                 len(analysis.get("set_comprehensions", [])) +
    #                 len(analysis.get("generator_expressions", []))
    #             )
    #         }
            
    #         return analysis
            
    #     except SyntaxError as e:
    #         return {
    #             "error": f"Syntax error in {file_name}: {str(e)}",
    #             "file_name": file_name,
    #             "line": e.lineno,
    #             "column": e.offset
    #         }
    #     except Exception as e:
    #         return {
    #             "error": f"Error analyzing {file_name}: {str(e)}",
    #             "file_name": file_name
    #         }
    
    # def print_analysis(self, analysis: Dict[str, Any]) -> None:
    #     """
    #     Print analysis results in a formatted way.
        
    #     Args:
    #         analysis: Analysis results dictionary
    #     """
    #     if "error" in analysis:
    #         print(f"❌ Error: {analysis['error']}")
    #         if "line" in analysis and "column" in analysis:
    #             print(f"   Location: Line {analysis['line']}, Column {analysis['column']}")
    #         return
        
    #     print(f"\n📊 Comprehensive Analysis Results for: {analysis['file_name']}")
    #     print("=" * 70)
        
    #     # File overview
    #     print(f"📄 File Overview:")
    #     print(f"   Total Lines: {analysis['total_lines']}")
    #     print(f"   Has Main Guard: {'Yes' if analysis['has_main_guard'] else 'No'}")
        
    #     # Summary statistics
    #     summary = analysis.get("summary", {})
    #     print(f"\n📈 Summary Statistics:")
    #     print(f"   Functions: {summary.get('total_functions', 0)}")
    #     print(f"   Classes: {summary.get('total_classes', 0)}")
    #     print(f"   Imports: {summary.get('total_imports', 0)}")
    #     print(f"   Variables: {summary.get('total_variables', 0)}")
    #     print(f"   Type Annotations: {summary.get('total_type_annotations', 0)}")
    #     print(f"   Control Flow: {summary.get('total_control_flow', 0)}")
    #     print(f"   Expressions: {summary.get('total_expressions', 0)}")
    #     print(f"   Comprehensions: {summary.get('total_comprehensions', 0)}")
        
    #     # Functions
    #     functions = analysis.get("functions", [])
    #     async_functions = analysis.get("async_functions", [])
    #     if functions or async_functions:
    #         print(f"\n🔧 Functions ({len(functions) + len(async_functions)}):")
    #         for func in functions:
    #             print(f"   • {func['name']}({', '.join(func['args'])}) - Line {func['line']}")
    #             if func.get('returns'):
    #                 print(f"     Returns: {func['returns']}")
    #             if func.get('decorators'):
    #                 print(f"     Decorators: {', '.join(func['decorators'])}")
    #         for func in async_functions:
    #             print(f"   • async {func['name']}({', '.join(func['args'])}) - Line {func['line']}")
    #             if func.get('returns'):
    #                 print(f"     Returns: {func['returns']}")
    #             if func.get('decorators'):
    #                 print(f"     Decorators: {', '.join(func['decorators'])}")
        
    #     # Classes
    #     classes = analysis.get("classes", [])
    #     if classes:
    #         print(f"\n🏗️  Classes ({len(classes)}):")
    #         for cls in classes:
    #             print(f"   • {cls['name']} - Line {cls['line']}")
    #             if cls.get('bases'):
    #                 print(f"     Bases: {', '.join(cls['bases'])}")
    #             if cls.get('decorators'):
    #                 print(f"     Decorators: {', '.join(cls['decorators'])}")
        
    #     # Imports
    #     imports = analysis.get("imports", [])
    #     from_imports = analysis.get("from_imports", [])
    #     if imports or from_imports:
    #         print(f"\n📦 Imports ({len(imports) + len(from_imports)}):")
    #         for imp in imports:
    #             name = f"{imp['module']} as {imp['asname']}" if imp['asname'] else imp['module']
    #             print(f"   • import {name}")
    #         for imp in from_imports:
    #             name = f"{imp['name']} as {imp['asname']}" if imp['asname'] else imp['name']
    #             print(f"   • from {imp['module']} import {name}")
        
    #     # Variables
    #     variables = analysis.get("variables", [])
    #     if variables:
    #         print(f"\n📝 Variables ({len(variables)}):")
    #         for var in variables[:10]:  # Show first 10
    #             context = []
    #             if var.get('parent_class'):
    #                 context.append(f"class {var['parent_class']}")
    #             if var.get('parent_function'):
    #                 context.append(f"function {var['parent_function']}")
    #             context_str = f" ({', '.join(context)})" if context else ""
    #             print(f"   • {var['name']}{context_str} - Line {var['line']}")
    #         if len(variables) > 10:
    #             print(f"   ... and {len(variables) - 10} more")
        
    #     # Type annotations
    #     type_annotations = analysis.get("type_annotations", [])
    #     if type_annotations:
    #         print(f"\n🏷️  Type Annotations ({len(type_annotations)}):")
    #         for ann in type_annotations[:5]:  # Show first 5
    #             print(f"   • {ann['type']}: {ann.get('target', 'N/A')} -> {ann.get('annotation', 'N/A')}")
    #         if len(type_annotations) > 5:
    #             print(f"   ... and {len(type_annotations) - 5} more")
        
    #     # Control flow
    #     if_blocks = analysis.get("if_statements", [])
    #     for_loops = analysis.get("for_loops", [])
    #     while_loops = analysis.get("while_loops", [])
    #     try_blocks = analysis.get("try_blocks", [])
        
    #     if if_blocks or for_loops or while_loops or try_blocks:
    #         print(f"\n🔄 Control Flow:")
    #         if if_blocks:
    #             print(f"   • If statements: {len(if_blocks)}")
    #         if for_loops:
    #             print(f"   • For loops: {len(for_loops)}")
    #         if while_loops:
    #             print(f"   • While loops: {len(while_loops)}")
    #         if try_blocks:
    #             print(f"   • Try blocks: {len(try_blocks)}")
        
    #     # Modern Python features
    #     match_statements = analysis.get("match_statements", [])
    #     named_expressions = analysis.get("named_expressions", [])
    #     f_strings = analysis.get("joined_strings", [])
        
    #     if match_statements or named_expressions or f_strings:
    #         print(f"\n✨ Modern Python Features:")
    #         if match_statements:
    #             print(f"   • Match statements: {len(match_statements)}")
    #         if named_expressions:
    #             print(f"   • Walrus operators: {len(named_expressions)}")
    #         if f_strings:
    #             print(f"   • F-strings: {len(f_strings)}")
        
    #     # Comprehensions
    #     comprehensions = (
    #         analysis.get("list_comprehensions", []) +
    #         analysis.get("dict_comprehensions", []) +
    #         analysis.get("set_comprehensions", []) +
    #         analysis.get("generator_expressions", [])
    #     )
    #     if comprehensions:
    #         print(f"\n📋 Comprehensions ({len(comprehensions)}):")
    #         list_comp = len(analysis.get("list_comprehensions", []))
    #         dict_comp = len(analysis.get("dict_comprehensions", []))
    #         set_comp = len(analysis.get("set_comprehensions", []))
    #         gen_comp = len(analysis.get("generator_expressions", []))
    #         if list_comp:
    #             print(f"   • List comprehensions: {list_comp}")
    #         if dict_comp:
    #             print(f"   • Dict comprehensions: {dict_comp}")
    #         if set_comp:
    #             print(f"   • Set comprehensions: {set_comp}")
    #         if gen_comp:
    #             print(f"   • Generator expressions: {gen_comp}")
        
    #     print("\n" + "=" * 70) 