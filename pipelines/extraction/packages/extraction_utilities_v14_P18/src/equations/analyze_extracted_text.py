"""
Analyze extracted text to understand equation patterns in Chapter 4 PDF
"""

import sys
import io
import warnings
from pathlib import Path

# Set UTF-8 encoding
if sys.platform == 'win32':
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, OSError, io.UnsupportedOperation):
            pass

# Import our simple extractor
# TODO: simple_equation_extractor module does not exist in v14
# This standalone analysis script needs to be updated or removed
# from simple_equation_extractor import SimpleEquationExtractor

def analyze_text_for_equations():
    """Analyze the extracted text to find equation patterns"""

    raise NotImplementedError(
        "This script depends on SimpleEquationExtractor which is not available in v14. "
        "Please use extraction_v14_P1 or specialized_extraction_v14_P15 instead."
    )

    # Create extractor and get text
    # extractor = SimpleEquationExtractor()
    text_content = extractor._extract_text_with_docling(Path('../../../tests/test_data/Ch-04_Heat_Transfer.pdf'))
    
    print(f"Text length: {len(text_content)} characters")
    
    # Look for lines that might contain equations
    lines = text_content.split('\n')
    potential_equations = []
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        # Look for patterns that might be equations
        if any(pattern in line for pattern in ['=', '(', ')', '°', 'π', 'α', 'β', 'σ', '∇', '∞']):
            if any(char.isdigit() for char in line):
                potential_equations.append((line_num, line))
    
    print(f"Found {len(potential_equations)} lines with potential equation content")
    
    # Show first 20 potential equations
    print("\n=== POTENTIAL EQUATION LINES ===")
    for i, (line_num, line) in enumerate(potential_equations[:20]):
        print(f"Line {line_num}: {line}")
        if i >= 19:
            print(f"... and {len(potential_equations) - 20} more")
            break
    
    # Look for numbered items specifically
    numbered_lines = []
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if '(' in line and ')' in line:
            # Extract potential equation numbers
            import re
            numbers = re.findall(r'\((\d+)\)', line)
            if numbers:
                numbered_lines.append((line_num, line, numbers))
    
    print(f"\nFound {len(numbered_lines)} lines with numbered patterns")
    print("\n=== NUMBERED PATTERNS ===")
    for i, (line_num, line, numbers) in enumerate(numbered_lines[:10]):
        print(f"Line {line_num} (numbers: {numbers}): {line}")
        if i >= 9:
            print(f"... and {len(numbered_lines) - 10} more")
            break
    
    # Look for specific physics terms
    physics_terms = ['fourier', 'heat', 'conduction', 'convection', 'radiation', 'thermal', 'temperature', 'newton', 'stefan', 'boltzmann']
    physics_lines = []
    
    for line_num, line in enumerate(lines, 1):
        line_lower = line.lower()
        if any(term in line_lower for term in physics_terms):
            if '=' in line or '(' in line:
                physics_lines.append((line_num, line))
    
    print(f"\nFound {len(physics_lines)} lines with physics terms and equation indicators")
    print("\n=== PHYSICS EQUATION LINES ===")
    for i, (line_num, line) in enumerate(physics_lines[:10]):
        print(f"Line {line_num}: {line}")
        if i >= 9:
            print(f"... and {len(physics_lines) - 10} more")
            break

if __name__ == "__main__":
    analyze_text_for_equations()