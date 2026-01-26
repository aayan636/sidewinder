import sys
import os
from pathlib import Path
from analysis.analyzer import PythonCodeAnalyzer


def main():
    """Main function to run the Python code analyzer."""
    
    # Check if file path is provided as command line argument
    if len(sys.argv) < 2:
        print("Usage: python driver.py <python_file_path>")
        print("Example: python driver.py example.py")
        return
    
    file_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File '{file_path}' does not exist.")
        return
    
    # Check if file is a Python file
    if not file_path.endswith('.py'):
        print(f"⚠️  Warning: File '{file_path}' doesn't have a .py extension.")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Create analyzer instance
    analyzer = PythonCodeAnalyzer()
    
    # Analyze the file
    print(f"🔍 Analyzing file: {file_path}")
    results = analyzer.analyze_file(file_path)
    
    # Print results
    analyzer.print_analysis(results)


if __name__ == "__main__":
    main()
