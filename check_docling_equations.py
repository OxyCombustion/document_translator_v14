from pathlib import Path
from docling.document_converter import DocumentConverter

pdf_path = Path("test_data/Ch-04_Heat_Transfer.pdf")
converter = DocumentConverter()

print("Converting PDF with Docling...")
result = converter.convert_single(pdf_path)

print("\nChecking for equations in result.output:")
if hasattr(result, 'output'):
    output = result.output
    if hasattr(output, 'equations'):
        equations = output.equations
        print(f"  Equations found: {len(equations)}")
        if len(equations) > 0:
            print(f"  First equation: {equations[0]}")
    else:
        print("  No 'equations' attribute")
else:
    print("  No 'output' attribute")
