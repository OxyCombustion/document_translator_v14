#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch 1 Full Extraction - Process 10 chapters with complete output preservation
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Batch 1 chapters configuration
BATCH_1_CHAPTERS = [
    ("Ch-53", "Nuclear_Waste_Management", "UNMJIZT3"),
    ("Ch-44", "Boiler_Operations", "CZ5R6KY4"),
    ("Ch-48", "Nuclear_Fuels", "62IBFRKL"),
    ("Ch-49", "Principles_of_Nuclear_Reactions", "B3STPXVQ"),
    ("Ch-08", "Structural", "8ZZ2YGRA"),
    ("Ch-11", "Oil_and_Gas", "6LVFMQNR"),
    ("Ch-46", "Condition_Assessment", "8LL8VREJ"),
    ("Ch-18", "Coal_Gasification", "VTT7N5JX"),
    ("Ch-52", "Nuclear_Services_Life_Ext", "W3E58GFD"),
    ("Ch-30", "Biomass", "QKSVHECM"),
]

# Configuration
ZOTERO_BASE = Path("/home/thermodynamics/windows_zotero/storage")
WEIGHTS_PATH = Path("/home/thermodynamics/document_translator_v14/models/doclayout_yolo_docstructbench_imgsz1024.pt")
BATCH_RESULTS_DIR = Path("/home/thermodynamics/document_translator_v14/batch_results")

def find_pdf(zotero_hash: str, chapter_prefix: str) -> Path:
    """Find the PDF file in Zotero storage"""
    storage_dir = ZOTERO_BASE / zotero_hash
    if not storage_dir.exists():
        raise FileNotFoundError(f"Storage directory not found: {storage_dir}")

    # Find PDF matching pattern
    pdfs = list(storage_dir.glob(f"{chapter_prefix}*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF found matching {chapter_prefix}*.pdf in {storage_dir}")

    if len(pdfs) > 1:
        print(f"⚠️  Warning: Multiple PDFs found, using first: {pdfs[0].name}")

    return pdfs[0]

def process_chapter(chapter_id: str, chapter_name: str, zotero_hash: str, batch_num: int, total: int):
    """Process a single chapter through the complete pipeline"""

    print(f"\n{'='*80}")
    print(f"📚 Processing {batch_num}/{total}: {chapter_id} - {chapter_name}")
    print(f"{'='*80}")

    start_time = time.time()

    try:
        # Find PDF
        pdf_path = find_pdf(zotero_hash, chapter_id)
        print(f"✅ Found PDF: {pdf_path.name}")

        # Setup output directory
        output_dir = BATCH_RESULTS_DIR / chapter_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Import and run pipeline inside exec to avoid import errors
        exec_code = f'''
import sys
from pathlib import Path

# Add project root to path
project_root = Path("/home/thermodynamics/document_translator_v14")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import pipeline components
from pipelines.rag_ingestion.packages.rag_v14_P2.src.orchestrators.unified_pipeline_orchestrator import UnifiedPipelineOrchestrator

# Initialize orchestrator with FULL output preservation
orchestrator = UnifiedPipelineOrchestrator(
    model_path="{str(WEIGHTS_PATH)}",
    output_dir="{str(output_dir)}",
    clean_before_run=True,
    enable_structured_output=True  # CRITICAL: Full extraction preservation
)

# Run complete pipeline
print("\\n🚀 Starting extraction phase...")
results = orchestrator.process_document(
    pdf_path=Path("{str(pdf_path)}"),
    num_workers=8
)

# Extract statistics from results
extraction_results = results.get("extraction", {{}})
extraction_stats = {{
    "equations": len(extraction_results.get("equations", [])),
    "tables": len(extraction_results.get("tables", [])),
    "figures": len(extraction_results.get("figures", [])),
    "text_blocks": len(extraction_results.get("text_blocks", [])),
    "success": True
}}
'''

        # Execute pipeline
        local_vars = {}
        exec(exec_code, {}, local_vars)
        extraction_stats = local_vars.get('extraction_stats', {})

        elapsed = time.time() - start_time

        # Print summary
        print(f"\n✅ SUCCESS: {chapter_id}")
        print(f"   📊 Extracted:")
        print(f"      - Equations: {extraction_stats.get('equations', 0)}")
        print(f"      - Tables: {extraction_stats.get('tables', 0)}")
        print(f"      - Figures: {extraction_stats.get('figures', 0)}")
        print(f"      - Text blocks: {extraction_stats.get('text_blocks', 0)}")
        print(f"   ⏱️  Time: {elapsed:.1f}s")
        print(f"   📁 Output: {output_dir}")

        return {
            "chapter_id": chapter_id,
            "chapter_name": chapter_name,
            "success": True,
            "stats": extraction_stats,
            "elapsed_time": elapsed,
            "output_dir": str(output_dir)
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ FAILED: {chapter_id}")
        print(f"   Error: {str(e)}")
        print(f"   Time: {elapsed:.1f}s")

        return {
            "chapter_id": chapter_id,
            "chapter_name": chapter_name,
            "success": False,
            "error": str(e),
            "elapsed_time": elapsed
        }

def main():
    """Run batch processing for all chapters"""

    print(f"\n{'#'*80}")
    print(f"# BATCH 1 FULL EXTRACTION - 10 Chapters")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}")

    # Verify prerequisites
    if not ZOTERO_BASE.exists():
        print(f"❌ ERROR: Zotero storage not found: {ZOTERO_BASE}")
        return 1

    if not WEIGHTS_PATH.exists():
        print(f"❌ ERROR: YOLO weights not found: {WEIGHTS_PATH}")
        return 1

    print(f"\n✅ Zotero storage: {ZOTERO_BASE}")
    print(f"✅ YOLO weights: {WEIGHTS_PATH}")
    print(f"✅ Output directory: {BATCH_RESULTS_DIR}")

    # Create results directory
    BATCH_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Process all chapters
    results = []
    total_chapters = len(BATCH_1_CHAPTERS)
    batch_start_time = time.time()

    for idx, (ch_id, ch_name, zh_hash) in enumerate(BATCH_1_CHAPTERS, 1):
        result = process_chapter(ch_id, ch_name, zh_hash, idx, total_chapters)
        results.append(result)

        # Save interim results
        interim_file = BATCH_RESULTS_DIR / "batch1_interim_results.json"
        with open(interim_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

    batch_elapsed = time.time() - batch_start_time

    # Final summary
    print(f"\n{'#'*80}")
    print(f"# BATCH 1 COMPLETE")
    print(f"{'#'*80}")

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n📊 Overall Statistics:")
    print(f"   ✅ Successful: {len(successful)}/{total_chapters}")
    print(f"   ❌ Failed: {len(failed)}/{total_chapters}")
    print(f"   ⏱️  Total time: {batch_elapsed/60:.1f} minutes")

    if successful:
        total_equations = sum(r['stats'].get('equations', 0) for r in successful)
        total_tables = sum(r['stats'].get('tables', 0) for r in successful)
        total_figures = sum(r['stats'].get('figures', 0) for r in successful)
        total_text = sum(r['stats'].get('text_blocks', 0) for r in successful)

        print(f"\n📈 Extraction Totals:")
        print(f"   - Equations: {total_equations}")
        print(f"   - Tables: {total_tables}")
        print(f"   - Figures: {total_figures}")
        print(f"   - Text blocks: {total_text}")

    if failed:
        print(f"\n❌ Failed Chapters:")
        for r in failed:
            print(f"   - {r['chapter_id']}: {r.get('error', 'Unknown error')}")

    # Save final results
    final_file = BATCH_RESULTS_DIR / "batch1_final_results.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump({
            "batch_name": "Batch 1 Full Extraction",
            "started": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_chapters": total_chapters,
            "successful": len(successful),
            "failed": len(failed),
            "total_time_minutes": batch_elapsed/60,
            "results": results
        }, f, indent=2)

    print(f"\n📁 Results saved to: {final_file}")
    print(f"\n✅ Batch processing complete!")

    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
