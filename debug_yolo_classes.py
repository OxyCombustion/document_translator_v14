#!/usr/bin/env python3
"""Debug script to check YOLO class names in Zone metadata"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from detection_v14_P14.src.doclayout.doclayout_equation_detector import DocLayoutEquationDetector

pdf_path = Path("test_data/Ch-04_Heat_Transfer.pdf")
output_dir = Path("results/debug_yolo")
output_dir.mkdir(parents=True, exist_ok=True)

detector = DocLayoutEquationDetector()

# Just process first 3 pages
import fitz
doc = fitz.open(pdf_path)

print("\nYOLO Class Names Found:")
print("=" * 80)

from doclayout_yolo import YOLOv10
import tempfile

model = detector.model

# Just check page 2 (has equations)
page = doc[1]  # Page 2 (0-indexed)
mat = fitz.Matrix(300/72, 300/72)
pix = page.get_pixmap(matrix=mat)

temp_dir = Path(tempfile.mkdtemp())
page_img = temp_dir / "page_2.png"
pix.save(str(page_img))

results = model.predict(str(page_img), imgsz=1024, conf=0.2, device='cpu')

for result in results:
    boxes = result.boxes
    print(f"\nPage 2 detections:")
    for box in boxes:
        cls_id = int(box.cls[0])
        cls_name = result.names[cls_id]
        conf = float(box.conf[0])

        if 'equation' in cls_name.lower() or 'formula' in cls_name.lower():
            print(f"  Class: '{cls_name}' (conf: {conf:.3f})")

doc.close()
page_img.unlink()
