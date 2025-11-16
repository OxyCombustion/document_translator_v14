#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parallel Equation Extractor - Multi-Core CPU Optimization
Uses batch processing with page arrays to minimize loading overhead
Based on successful parallel_table_extractor.py architecture

Focus: ACCURACY FIRST, then performance
Key Fix: Search UPSTREAM (before) equation numbers, not downstream
"""

import sys
import os
from pathlib import Path
import tempfile
import time
import json
import re
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

class ParallelEquationExtractor:
    """Multi-core equation extractor using batch processing to minimize loading overhead"""
    
    def __init__(self):
        self.pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
        self.target_equation_count = 106
        self.extracted_equations = []
        
        # Calculate optimal worker configuration (same as table extractor)
        self.total_cores = cpu_count()
        self.max_workers = min(8, max(2, self.total_cores - 2))  # Leave 2 cores for system
        
    def batch_worker(self, page_batch, worker_id):
        """
        Worker function that processes a batch of pages for equation extraction
        Uses PyMuPDF directly (no Docling needed for equation extraction)
        """
        print(f"🔄 Worker {worker_id}: Processing {len(page_batch)} pages {page_batch}")
        
        worker_start_time = time.time()
        batch_results = []
        
        try:
            # Import PyMuPDF for this worker
            import fitz
            
            # Open PDF once per batch (key optimization)
            doc = fitz.open(self.pdf_path)
            loading_time = time.time() - worker_start_time
            print(f"📦 Worker {worker_id}: PDF loaded in {loading_time:.1f}s")
            
            # Process all pages in this batch with the same PDF instance
            for page_num in page_batch:
                page_start_time = time.time()
                
                try:
                    # Extract equations from single page
                    page_equations = self.extract_equations_from_page(
                        doc, page_num, worker_id
                    )
                    
                    if page_equations:
                        batch_results.extend(page_equations)
                        page_time = time.time() - page_start_time
                        eq_numbers = [eq['equation_number'] for eq in page_equations]
                        print(f"✅ Worker {worker_id}: Page {page_num} found equations {eq_numbers} in {page_time:.1f}s")
                    else:
                        page_time = time.time() - page_start_time
                        print(f"❌ Worker {worker_id}: Page {page_num} no equations found ({page_time:.1f}s)")
                        
                except Exception as e:
                    page_time = time.time() - page_start_time
                    print(f"❌ Worker {worker_id}: Page {page_num} error: {e} ({page_time:.1f}s)")
            
            doc.close()
            worker_total_time = time.time() - worker_start_time
            print(f"🎯 Worker {worker_id}: Batch complete - {len(batch_results)} equations in {worker_total_time:.1f}s")
            
            return batch_results
            
        except Exception as e:
            worker_total_time = time.time() - worker_start_time
            print(f"❌ Worker {worker_id}: Critical error: {e} ({worker_total_time:.1f}s)")
            return []
    
    def extract_equations_from_page(self, doc, page_num, worker_id):
        """Extract equations from single page using corrected UPSTREAM search"""
        
        page = doc[page_num - 1]  # PyMuPDF uses 0-based indexing
        page_text = page.get_text()
        
        # Find all equation numbers on this page
        equation_pattern = r'\((\d+)\)'
        matches = list(re.finditer(equation_pattern, page_text))
        
        page_equations = []
        for match in matches:
            equation_number = int(match.group(1))
            
            # Only process valid equation number range
            if 1 <= equation_number <= 106:
                equation_data = self.extract_equation_upstream_corrected(
                    page_text, match, equation_number, page_num, worker_id
                )
                
                if equation_data and self.is_valid_mathematical_equation(equation_data):
                    page_equations.append(equation_data)
        
        return page_equations
    
    def extract_equation_upstream_corrected(self, page_text, number_match, equation_number, page_num, worker_id):
        """
        CORRECTED METHOD: Search UPSTREAM (before) equation number for mathematical content
        This fixes the critical direction error discovered in our analysis
        """
        
        number_pos = number_match.start()
        
        # Search UPSTREAM (before) the equation number - CORRECTED APPROACH
        search_start = max(0, number_pos - 500)  # Look back up to 500 characters
        upstream_text = page_text[search_start:number_pos]
        
        # Split into lines and work backwards from equation number
        lines = upstream_text.split('\n')
        
        equation_lines = []
        for line in reversed(lines):
            line = line.strip()
            
            if not line:
                if equation_lines:  # Stop at empty line after finding content
                    break
                continue
            
            # Check if this line has strong mathematical content
            if self.has_strong_mathematical_content(line):
                equation_lines.insert(0, line)
            elif equation_lines:
                # If we've found math content and this line doesn't have it, stop
                # Unless it's a short connector line
                if len(line) > 15 and not self.has_weak_mathematical_content(line):
                    break
                equation_lines.insert(0, line)
            else:
                # Check if this could be start of equation (even without strong math)
                if self.could_be_equation_start(line):
                    equation_lines.insert(0, line)
        
        if not equation_lines:
            return None
        
        equation_text = ' '.join(equation_lines).strip()
        
        # Score the equation candidate
        score = self.score_equation_candidate(equation_text)
        
        # Must meet minimum score threshold
        if score < 2.0:
            return None
        
        return {
            'equation_id': f'Equation_{equation_number}',
            'equation_number': str(equation_number),
            'page': page_num,
            'raw_text': equation_text,
            'direction': 'upstream_corrected',
            'score': score,
            'worker_id': worker_id,
            'extraction_method': 'parallel_upstream_pymupdf'
        }
    
    def has_strong_mathematical_content(self, text):
        """Check for strong mathematical indicators"""
        if len(text.strip()) < 3:
            return False
        
        # Strong mathematical indicators
        strong_math = [
            '=',           # Equals sign
            '∇', '∂', '∆', # Calculus operators
            '∑', '∫', '√', # Mathematical operators
            'α', 'β', 'γ', 'δ', 'ε', 'μ', 'ρ', 'σ', 'τ', 'π', 'φ', 'λ', 'ω', # Greek letters
        ]
        
        strong_count = sum(text.count(symbol) for symbol in strong_math)
        
        # Mathematical patterns
        has_fraction = bool(re.search(r'\w+/\w+', text))
        has_exponent = bool(re.search(r'\w+\^\w+', text))
        has_subscript = bool(re.search(r'\w+_\w+', text))
        
        # Strong if multiple indicators or clear patterns
        return (strong_count >= 2 or 
                has_fraction or 
                has_exponent or 
                has_subscript or
                (strong_count >= 1 and len(text) < 40))  # Short with math symbols
    
    def has_weak_mathematical_content(self, text):
        """Check for weak mathematical indicators (connectors, variables)"""
        weak_math = ['+', '-', '*', '/', '(', ')', '[', ']', '^', '_']
        has_variables = bool(re.search(r'\b[a-zA-Z]\b', text))
        has_weak_symbols = any(symbol in text for symbol in weak_math)
        
        return has_variables and has_weak_symbols
    
    def could_be_equation_start(self, text):
        """Check if line could be start of equation (less strict)"""
        # Mathematical variables or constants
        math_variables = ['h', 'k', 'T', 'A', 'q', 'Nu', 'Re', 'Pr', 'Gr', 'Ra', 'Bi', 'Fo']
        has_math_var = any(var in text for var in math_variables)
        
        # Basic mathematical symbols
        has_basic_math = any(symbol in text for symbol in ['=', '+', '-', '/', '*'])
        
        return has_math_var or has_basic_math
    
    def score_equation_candidate(self, equation_text):
        """Score equation candidate quality"""
        if not equation_text:
            return 0
        
        score = 0
        
        # Strong mathematical symbols (3 points each)
        strong_symbols = ['=', '∇', '∂', '∆', '∑', '∫', '√']
        score += sum(equation_text.count(symbol) * 3 for symbol in strong_symbols)
        
        # Greek letters (2 points each)
        greek_letters = ['α', 'β', 'γ', 'δ', 'ε', 'μ', 'ρ', 'σ', 'τ', 'π', 'φ', 'λ', 'ω']
        score += sum(equation_text.count(letter) * 2 for letter in greek_letters)
        
        # Heat transfer specific variables (1.5 points each)
        heat_vars = ['Nu', 'Re', 'Pr', 'Gr', 'Ra', 'Bi', 'Fo', 'hc', 'kf']
        for var in heat_vars:
            score += equation_text.count(var) * 1.5
        
        # Mathematical operators (1 point each)
        operators = ['+', '-', '*', '/', '^', '_']
        score += sum(equation_text.count(op) * 1 for op in operators)
        
        # Variables (single letters) (0.3 points each)
        variables = len(re.findall(r'\b[a-zA-Z]\b', equation_text))
        score += variables * 0.3
        
        # Pattern bonuses
        if re.search(r'\w+/\w+', equation_text):  # Fractions
            score += 3
        if re.search(r'\w+\^\w+', equation_text):  # Exponents
            score += 2
        if re.search(r'\w+_\w+', equation_text):   # Subscripts
            score += 1
        
        # Length bonuses/penalties
        if 5 <= len(equation_text) <= 50:  # Optimal length
            score += 2
        elif len(equation_text) > 150:  # Very long (likely false positive)
            score -= 3
        
        # Penalties for non-equation content
        false_indicators = ['Figure', 'Table', 'Page', 'Chapter', 'Note:', 'See', 'where:']
        for indicator in false_indicators:
            if indicator in equation_text:
                score -= 4
        
        # Penalty for obvious descriptive text
        if len(equation_text.split()) > 10:  # Many words
            word_to_symbol_ratio = len(equation_text.split()) / max(1, equation_text.count('=') + equation_text.count('+') + equation_text.count('-'))
            if word_to_symbol_ratio > 5:  # Too wordy
                score -= 2
        
        return max(0, score)  # Don't return negative scores
    
    def is_valid_mathematical_equation(self, equation_data):
        """Final validation that this is a mathematical equation"""
        
        # Must have minimum score
        if equation_data['score'] < 2.0:
            return False
        
        text = equation_data['raw_text']
        
        # Must have some mathematical content
        if not (self.has_strong_mathematical_content(text) or 
                self.has_weak_mathematical_content(text)):
            return False
        
        # Must not be obvious false positives
        false_positive_patterns = [
            r'do not allow transmission',
            r'limit according to',
            r'Steam \d+',
            r'Heat Transfer$',
            r'Babcock.*Wilcox',
            r'^\d+-\d+$',  # Page numbers
            r'Chapter \d+',
            r'Figure \d+',
            r'Table \d+'
        ]
        
        for pattern in false_positive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        return True
    
    def create_page_batches(self):
        """Create optimal page batches for equation extraction"""
        
        # For equations, we need to check all pages (unlike tables which are on specific pages)
        import fitz
        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        doc.close()
        
        all_pages = list(range(1, total_pages + 1))
        
        # Calculate pages per batch
        if total_pages <= self.max_workers:
            # Few pages: 1 page per worker
            pages_per_batch = 1
        else:
            # More pages: distribute evenly across workers  
            pages_per_batch = (total_pages + self.max_workers - 1) // self.max_workers
        
        page_batches = []
        for i in range(0, total_pages, pages_per_batch):
            batch = all_pages[i:i + pages_per_batch]
            page_batches.append(batch)
        
        print(f"📊 Parallel Configuration:")
        print(f"   Total pages to process: {total_pages}")
        print(f"   Total cores available: {self.total_cores}")
        print(f"   Max workers: {self.max_workers}")
        print(f"   Pages per batch: {pages_per_batch}")
        print(f"   Total batches: {len(page_batches)}")
        print(f"   Batch distribution: {page_batches[:3]}...")  # Show first few batches
        
        return page_batches
    
    def run_parallel_extraction(self):
        """Run parallel equation extraction with batch processing optimization"""
        
        print("🚀 PARALLEL EQUATION EXTRACTION - MULTI-CORE CPU OPTIMIZATION")
        print("==" * 35)
        
        print(f"📄 Processing PDF: {self.pdf_path}")
        print(f"🎯 Target equations: {self.target_equation_count}")
        print(f"🔧 CORRECTED: Searching UPSTREAM (before) equation numbers")
        
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
                    self.extracted_equations.extend(batch_results)
                    eq_numbers = [eq['equation_number'] for eq in batch_results] if batch_results else []
                    print(f"✅ Batch {batch} completed: {len(batch_results)} equations {eq_numbers}")
                except Exception as e:
                    print(f"❌ Batch {batch} failed: {e}")
        
        # Sort equations by equation number
        self.extracted_equations.sort(key=lambda x: int(x['equation_number']))
        
        total_time = time.time() - total_start_time
        
        print(f"\n🎉 === PARALLEL EXTRACTION COMPLETE ===")
        print(f"✅ Total equations extracted: {len(self.extracted_equations)}")
        print(f"⏱️  Total processing time: {total_time:.1f}s")
        print(f"🎯 Target: {self.target_equation_count}")
        print(f"📈 Success rate: {len(self.extracted_equations)}/{self.target_equation_count} ({len(self.extracted_equations)/self.target_equation_count*100:.1f}%)")
        
        if total_time > 0:
            pages_per_minute = len(page_batches) / (total_time / 60)
            print(f"⚡ Processing rate: {pages_per_minute:.1f} page batches per minute")
        
        # Create output file
        if self.extracted_equations:
            self.create_parallel_equation_output()
        else:
            print("❌ No equations extracted")
        
        return True
    
    def create_parallel_equation_output(self):
        """Create comprehensive equation extraction output"""
        print(f"\n📁 === CREATING PARALLEL EQUATION OUTPUT ===")
        
        # Create detailed results JSON
        output_data = {
            "metadata": {
                "document": "Ch-04_Heat_Transfer.pdf",
                "extraction_method": "Parallel CPU with UPSTREAM search (corrected)",
                "target_equations": self.target_equation_count,
                "extracted_equations": len(self.extracted_equations),
                "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "success_rate": f"{len(self.extracted_equations)}/{self.target_equation_count} ({len(self.extracted_equations)/self.target_equation_count*100:.1f}%)",
                "direction_correction": "Fixed to search UPSTREAM (before) equation numbers"
            },
            "statistics": {
                "total_equations": len(self.extracted_equations),
                "equation_numbers": [eq['equation_number'] for eq in self.extracted_equations],
                "worker_distribution": {},
                "score_analysis": {
                    "average_score": sum(eq['score'] for eq in self.extracted_equations) / len(self.extracted_equations) if self.extracted_equations else 0,
                    "score_range": f"{min(eq['score'] for eq in self.extracted_equations):.1f} to {max(eq['score'] for eq in self.extracted_equations):.1f}" if self.extracted_equations else "None",
                    "high_confidence": len([eq for eq in self.extracted_equations if eq['score'] >= 5.0])
                }
            },
            "equations": self.extracted_equations
        }
        
        # Analyze worker distribution
        for eq in self.extracted_equations:
            worker_id = eq.get('worker_id', 'unknown')
            if worker_id not in output_data["statistics"]["worker_distribution"]:
                output_data["statistics"]["worker_distribution"][worker_id] = 0
            output_data["statistics"]["worker_distribution"][worker_id] += 1
        
        output_path = "results/Chapter4_Parallel_Equations.json"
        os.makedirs("results", exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Parallel equations JSON created: {output_path}")
            
            # Show sample equations for manual verification
            print(f"\n📝 Sample extracted equations (first 5):")
            for i, eq in enumerate(self.extracted_equations[:5]):
                print(f"   {i+1}. Eq ({eq['equation_number']}) [Score:{eq['score']:.1f}]: {eq['raw_text'][:60]}...")
            
            if len(self.extracted_equations) > 5:
                print(f"   ... and {len(self.extracted_equations) - 5} more equations")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Output creation failed: {e}")
            return False

def main():
    """Main execution with performance and accuracy measurement"""
    
    print("🎯 PARALLEL EQUATION EXTRACTION - ACCURACY FIRST, PERFORMANCE SECOND")
    print("=" * 70)
    
    extractor = ParallelEquationExtractor()
    
    print(f"📋 System Configuration:")
    print(f"   Available CPU cores: {multiprocessing.cpu_count()}")
    print(f"   Target equations: {extractor.target_equation_count}")
    print(f"   🔧 CRITICAL FIX: Searching UPSTREAM from equation numbers")
    print(f"   🎯 Priority: ACCURACY over speed\\n")
    
    success = extractor.run_parallel_extraction()
    
    if success:
        print(f"\\n✅ SUCCESS: Parallel equation extraction complete!")
        print(f"📁 Results saved: results/Chapter4_Parallel_Equations.json")
        print(f"🔍 NEXT: Manual accuracy verification against PDF content")
        print(f"⚠️  REMEMBER: Verify accuracy BEFORE celebrating performance")
    else:
        print(f"\\n❌ FAILED: Parallel equation extraction encountered errors")

if __name__ == "__main__":
    main()