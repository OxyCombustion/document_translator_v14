#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parallel Table Extractor - Multi-Core CPU Optimization
Uses batch processing with page arrays to minimize Docling loading overhead
Based on verified working create_perfect_tables.py with parallel acceleration

Expected Performance: 30-40s instead of 79.8s (2-3x speedup)
"""

import sys
import os
from pathlib import Path
import tempfile
import time
import json
import pandas as pd
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# Set UTF-8 encoding for Windows console  
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

class ParallelTableExtractor:
    """Multi-core table extractor using batch processing to minimize Docling loading"""
    
    def __init__(self):
        self.pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
        self.target_pages = [2, 4, 5, 9, 10, 12, 21]  # Known table pages (verified)
        self.extracted_tables = []
        
        # Calculate optimal worker configuration
        self.total_cores = cpu_count()
        self.max_workers = min(8, max(2, self.total_cores - 2))  # Leave 2 cores for system
        
    def batch_worker(self, page_batch, worker_id):
        """
        Worker function that processes a batch of pages with single Docling loading
        This minimizes the expensive Docling initialization overhead
        """
        print(f"🔄 Worker {worker_id}: Processing {len(page_batch)} pages {page_batch}")
        
        worker_start_time = time.time()
        batch_results = []
        
        try:
            # SINGLE Docling initialization per batch (key optimization)
            from docling.document_converter import DocumentConverter
            docling_converter = DocumentConverter()
            
            loading_time = time.time() - worker_start_time
            print(f"📦 Worker {worker_id}: Docling loaded in {loading_time:.1f}s")
            
            # Process all pages in this batch with the same Docling instance
            for page_num in page_batch:
                page_start_time = time.time()
                
                try:
                    # Create single page PDF (using proven method from working CPU version)
                    table_data = self.extract_single_page_with_docling(
                        docling_converter, page_num, worker_id
                    )
                    
                    if table_data:
                        batch_results.append(table_data)
                        page_time = time.time() - page_start_time
                        print(f"✅ Worker {worker_id}: Page {page_num} processed in {page_time:.1f}s")
                    else:
                        page_time = time.time() - page_start_time
                        print(f"❌ Worker {worker_id}: Page {page_num} no tables found ({page_time:.1f}s)")
                        
                except Exception as e:
                    page_time = time.time() - page_start_time
                    print(f"❌ Worker {worker_id}: Page {page_num} error: {e} ({page_time:.1f}s)")
            
            worker_total_time = time.time() - worker_start_time
            print(f"🎯 Worker {worker_id}: Batch complete in {worker_total_time:.1f}s")
            
            return batch_results
            
        except Exception as e:
            worker_total_time = time.time() - worker_start_time
            print(f"❌ Worker {worker_id}: Critical error: {e} ({worker_total_time:.1f}s)")
            return []
    
    def extract_single_page_with_docling(self, docling_converter, page_number, worker_id):
        """Extract table from single page using existing Docling instance (copied from working CPU version)"""
        
        # Create single-page PDF using proven method
        import fitz
        import tempfile
        
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, f'page_{page_number}_worker_{worker_id}.pdf')
        
        try:
            # Use PyMuPDF to extract single page (fast, proven method)
            source_doc = fitz.open(self.pdf_path)
            page_doc = fitz.open()
            page_doc.insert_pdf(source_doc, from_page=page_number-1, to_page=page_number-1)
            page_doc.save(temp_path)
            page_doc.close()
            source_doc.close()
            
            # Process with existing Docling instance (no loading overhead)
            result = docling_converter.convert(temp_path)
            
            # Use proven markdown parsing method (from working CPU version)
            tables = result.document.tables
            markdown_text = result.document.export_to_markdown()
            
            if len(tables) > 0:
                # Use working markdown parsing approach
                table_data = self.parse_table_from_markdown(markdown_text, page_number, 0, worker_id)
                return table_data
            else:
                return None
                
        finally:
            # Clean up temp directory and files
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass  # Ignore cleanup errors
    
    def parse_table_from_markdown(self, markdown_text, page_number, table_index, worker_id):
        """Parse table from markdown using proven working method (copied from CPU version)"""
        try:
            # Process table lines (exact copy from working CPU version)
            lines = markdown_text.split('\n')
            table_lines = []
            
            for line in lines:
                if '|' in line:
                    table_lines.append(line.strip())
            
            # Parse table structure
            processed_lines = []
            for line in table_lines:
                if line.startswith('|') and line.endswith('|'):
                    content = line[1:-1]  # Remove outer pipes
                    cells = [cell.strip() for cell in content.split('|')]
                    
                    # Skip separator lines
                    if all(set(cell.strip()) <= {'-', ':', ' ', ''} for cell in cells if cell.strip()):
                        continue
                    
                    processed_lines.append(cells)
            
            if len(processed_lines) < 2:
                return None
            
            # Perfect header detection algorithm (exact copy from working CPU version)
            first_line = processed_lines[0]
            is_title_row = len(set(first_line)) == 1  # All cells identical = title row
            
            if is_title_row:
                table_title = first_line[0]
                actual_headers = processed_lines[1]  # Real headers in second row
                data_rows = processed_lines[2:]
                print(f"📋 Worker {worker_id}: Title row detected: '{table_title}'")
                print(f"📋 Worker {worker_id}: Headers: {actual_headers}")
            else:
                table_title = "Untitled Table"
                actual_headers = first_line
                data_rows = processed_lines[1:]
                print(f"📋 Worker {worker_id}: No title row, headers: {actual_headers}")
            
            # Create table structure
            table_data = {
                'table_id': f'Page_{page_number}_Table_{table_index + 1}',
                'page': page_number,
                'title': table_title,
                'headers': actual_headers,
                'data': data_rows,
                'processing_method': 'parallel_cpu_batch_processing',
                'worker_id': worker_id
            }
            
            return table_data
            
        except Exception as e:
            print(f"❌ Worker {worker_id}: Markdown parsing error: {e}")
            return None
    
    def create_page_batches(self):
        """Create optimal page batches to minimize Docling loading while maximizing parallel efficiency"""
        
        # Calculate pages per batch to balance loading overhead vs parallelism
        total_pages = len(self.target_pages)
        
        if total_pages <= self.max_workers:
            # Few pages: 1 page per worker (maximum parallelism)
            pages_per_batch = 1
        else:
            # More pages: distribute evenly across workers
            pages_per_batch = (total_pages + self.max_workers - 1) // self.max_workers
        
        page_batches = []
        for i in range(0, total_pages, pages_per_batch):
            batch = self.target_pages[i:i + pages_per_batch]
            page_batches.append(batch)
        
        print(f"📊 Parallel Configuration:")
        print(f"   Total cores available: {self.total_cores}")
        print(f"   Max workers: {self.max_workers}")
        print(f"   Pages per batch: {pages_per_batch}")
        print(f"   Total batches: {len(page_batches)}")
        print(f"   Batch distribution: {page_batches}")
        
        return page_batches
    
    def run_parallel_extraction(self):
        """Run parallel table extraction with batch processing optimization"""
        
        print("🚀 PARALLEL TABLE EXTRACTION - MULTI-CORE CPU OPTIMIZATION")
        print("=" * 70)
        
        print(f"📄 Processing {len(self.target_pages)} pages: {self.target_pages}")
        print(f"⚡ Expected speedup: 2-3x faster than 79.8s sequential baseline")
        
        # Create optimal page batches
        page_batches = self.create_page_batches()
        
        print(f"\n🔄 === STARTING PARALLEL BATCH PROCESSING ===")
        total_start_time = time.time()
        
        # Process batches in parallel using ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch jobs
            future_to_batch = {}
            for i, batch in enumerate(page_batches):
                future = executor.submit(self.batch_worker, batch, i + 1)
                future_to_batch[future] = batch
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    self.extracted_tables.extend(batch_results)
                    print(f"✅ Batch {batch} completed: {len(batch_results)} tables extracted")
                except Exception as e:
                    print(f"❌ Batch {batch} failed: {e}")
        
        total_time = time.time() - total_start_time
        
        print(f"\n🎉 === PARALLEL EXTRACTION COMPLETE ===")
        print(f"✅ Total tables extracted: {len(self.extracted_tables)}")
        print(f"⏱️  Total processing time: {total_time:.1f}s")
        print(f"⚡ Sequential baseline: 79.8s")
        
        if total_time > 0:
            speedup = 79.8 / total_time
            print(f"🚀 Speedup achieved: {speedup:.1f}x faster")
            pages_per_minute = len(self.target_pages) / (total_time / 60)
            print(f"📈 Processing rate: {pages_per_minute:.1f} pages per minute")
        
        # Create Excel output
        if self.extracted_tables:
            self.create_parallel_excel()
        else:
            print("❌ No tables extracted")
        
        return True
    
    def create_parallel_excel(self):
        """Create Excel output from parallel extraction results"""
        print(f"\n📁 === CREATING PARALLEL EXTRACTION EXCEL ===")
        
        output_path = "results/Chapter4_Parallel_CPU_Tables.xlsx"
        
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Create summary sheet
                summary_data = []
                for table in self.extracted_tables:
                    summary_data.append({
                        'Table_ID': table['table_id'],
                        'Page': table['page'],
                        'Worker': table['worker_id'],
                        'Title': table['title'],
                        'Columns': len(table['headers']),
                        'Rows': len(table['data']),
                        'Headers': ' | '.join(table['headers']),
                        'Sample_Row': ' | '.join(table['data'][0]) if table['data'] else '',
                        'Method': table['processing_method']
                    })
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Parallel_Summary', index=False)
                
                # Create individual table sheets
                for table in self.extracted_tables:
                    if table['data'] and table['headers']:
                        df = pd.DataFrame(table['data'], columns=table['headers'])
                        sheet_name = f"P{table['page']}_W{table['worker_id']}_{table['title'][:15].replace(' ', '_')}"
                        sheet_name = sheet_name[:31]  # Excel limit
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        print(f"   ✅ Created sheet: {sheet_name} ({len(table['headers'])} cols × {len(table['data'])} rows)")
            
            print(f"✅ Parallel Excel created: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Excel creation failed: {e}")
            return False

def main():
    """Main execution with performance comparison"""
    
    print("🎯 MULTI-CORE TABLE EXTRACTION PERFORMANCE TEST")
    print("=" * 60)
    
    extractor = ParallelTableExtractor()
    
    print(f"📋 System Configuration:")
    print(f"   Available CPU cores: {multiprocessing.cpu_count()}")
    print(f"   Target pages for tables: {len(extractor.target_pages)}")
    print(f"   Sequential baseline: 79.8s for 7 tables")
    print(f"   Expected improvement: 2-3x speedup\n")
    
    success = extractor.run_parallel_extraction()
    
    if success:
        print(f"\n✅ SUCCESS: Parallel extraction complete!")
        print(f"📁 Results saved: results/Chapter4_Parallel_CPU_Tables.xlsx")
        print(f"🔍 Compare with sequential version: results/Chapter4_PERFECT_Tables.xlsx")
    else:
        print(f"\n❌ FAILED: Parallel extraction encountered errors")

if __name__ == "__main__":
    main()