#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bidirectional Equation Extractor
Handles equation numbers positioned either before OR after the mathematical content
"""

import sys
import os
from pathlib import Path
import json
import time
import re

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

class BidirectionalEquationExtractor:
    """Extract equations with numbers positioned either before or after mathematical content"""
    
    def __init__(self):
        self.pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
        self.target_equation_count = 106
        self.extracted_equations = []
        
    def extract_equations_bidirectionally(self):
        """Extract equations checking both directions from equation numbers"""
        print("🔄 === BIDIRECTIONAL EQUATION EXTRACTION ===")
        print(f"📄 PDF: {self.pdf_path}")
        print(f"🔍 Searching both directions from equation numbers")
        print("=" * 60)
        
        try:
            import fitz
            
            doc = fitz.open(self.pdf_path)
            all_equations = []
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                # Find all equation numbers on this page
                equation_pattern = r'\((\d+)\)'
                matches = list(re.finditer(equation_pattern, page_text))
                
                page_equations = []
                for match in matches:
                    equation_number = int(match.group(1))
                    
                    # Only process valid equation number range
                    if 1 <= equation_number <= 106:
                        equation_data = self.extract_equation_bidirectionally(
                            page_text, match, equation_number, page_num + 1
                        )
                        
                        if equation_data and self.is_valid_mathematical_equation(equation_data):
                            page_equations.append(equation_data)
                
                if page_equations:
                    all_equations.extend(page_equations)
                    numbers = [eq['equation_number'] for eq in page_equations]
                    print(f"   📄 Page {page_num + 1:2d}: Found equations {numbers}")
            
            doc.close()
            
            # Sort by equation number
            all_equations.sort(key=lambda x: int(x['equation_number']))
            
            print(f"\n📊 BIDIRECTIONAL EXTRACTION RESULTS:")
            print(f"   ✅ Total equations found: {len(all_equations)}")
            print(f"   🎯 Target: {self.target_equation_count}")
            print(f"   📈 Success rate: {len(all_equations)}/{self.target_equation_count} ({len(all_equations)/self.target_equation_count*100:.1f}%)")
            
            self.extracted_equations = all_equations
            return all_equations
            
        except Exception as e:
            print(f"❌ Bidirectional extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_equation_bidirectionally(self, page_text, number_match, equation_number, page_num):
        """Extract equation content checking both before and after the number"""
        
        number_pos = number_match.start()
        number_end = number_match.end()
        
        # Get context windows
        context_size = 300
        start_pos = max(0, number_pos - context_size)
        end_pos = min(len(page_text), number_end + context_size)
        full_context = page_text[start_pos:end_pos]
        
        # Try both directions
        before_equation = self.extract_equation_before_number(page_text, number_pos)
        after_equation = self.extract_equation_after_number(page_text, number_end)
        
        # Score both candidates
        before_score = self.score_equation_candidate(before_equation) if before_equation else 0
        after_score = self.score_equation_candidate(after_equation) if after_equation else 0
        
        # Choose the better candidate
        if before_score > after_score and before_score > 3:
            chosen_equation = before_equation
            direction = "before"
            score = before_score
        elif after_score > 3:
            chosen_equation = after_equation  
            direction = "after"
            score = after_score
        else:
            # Neither candidate is strong enough
            return None
        
        return {
            'equation_id': f'Equation_{equation_number}',
            'equation_number': str(equation_number),
            'page': page_num,
            'raw_text': chosen_equation,
            'direction': direction,
            'score': score,
            'before_candidate': before_equation,
            'after_candidate': after_equation,
            'before_score': before_score,
            'after_score': after_score,
            'context': full_context[:200] + '...',
            'extraction_method': 'bidirectional_pymupdf'
        }
    
    def extract_equation_before_number(self, page_text, number_pos):
        """Extract mathematical content before the equation number"""
        
        # Look backward from the number position
        search_start = max(0, number_pos - 400)
        before_text = page_text[search_start:number_pos]
        
        # Split into lines and work backwards
        lines = before_text.split('\n')
        
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
                if len(line) > 10 and not self.has_weak_mathematical_content(line):
                    break
                equation_lines.insert(0, line)
            else:
                # Haven't found math content yet, keep looking
                continue
        
        if equation_lines:
            return ' '.join(equation_lines).strip()
        return None
    
    def extract_equation_after_number(self, page_text, number_end):
        """Extract mathematical content after the equation number"""
        
        # Look forward from the number position  
        search_end = min(len(page_text), number_end + 400)
        after_text = page_text[number_end:search_end]
        
        # Split into lines and work forwards
        lines = after_text.split('\n')
        
        equation_lines = []
        for line in lines:
            line = line.strip()
            
            if not line:
                if equation_lines:  # Stop at empty line after finding content
                    break
                continue
            
            # Check if this line has strong mathematical content
            if self.has_strong_mathematical_content(line):
                equation_lines.append(line)
            elif equation_lines:
                # If we've found math content and this line doesn't have it, stop
                # Unless it's a short connector line
                if len(line) > 10 and not self.has_weak_mathematical_content(line):
                    break
                equation_lines.append(line)
            else:
                # Haven't found math content yet, keep looking
                continue
        
        if equation_lines:
            return ' '.join(equation_lines).strip()
        return None
    
    def has_strong_mathematical_content(self, text):
        """Check for strong mathematical indicators"""
        if len(text.strip()) < 3:
            return False
        
        # Strong mathematical indicators
        strong_math = [
            '=',           # Equals sign
            '∇', '∂', '∆', # Calculus operators
            '∑', '∫', '√', # Mathematical operators
            'α', 'β', 'γ', 'δ', 'ε', 'μ', 'ρ', 'σ', 'τ', 'π', 'φ', # Greek letters
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
                (strong_count >= 1 and len(text) < 30))  # Short with math symbols
    
    def has_weak_mathematical_content(self, text):
        """Check for weak mathematical indicators (connectors, variables)"""
        weak_math = ['+', '-', '*', '/', '(', ')', '[', ']']
        has_variables = bool(re.search(r'\b[a-zA-Z]\b', text))
        has_weak_symbols = any(symbol in text for symbol in weak_math)
        
        return has_variables and has_weak_symbols
    
    def score_equation_candidate(self, equation_text):
        """Score equation candidate quality"""
        if not equation_text:
            return 0
        
        score = 0
        
        # Strong mathematical symbols (2 points each)
        strong_symbols = ['=', '∇', '∂', '∆', '∑', '∫', '√']
        score += sum(equation_text.count(symbol) * 2 for symbol in strong_symbols)
        
        # Greek letters (1.5 points each)
        greek_letters = ['α', 'β', 'γ', 'δ', 'ε', 'μ', 'ρ', 'σ', 'τ', 'π', 'φ']
        score += sum(equation_text.count(letter) * 1.5 for letter in greek_letters)
        
        # Mathematical operators (0.5 points each)
        operators = ['+', '-', '*', '/', '^', '_']
        score += sum(equation_text.count(op) * 0.5 for op in operators)
        
        # Variables (single letters) (0.2 points each)
        variables = len(re.findall(r'\b[a-zA-Z]\b', equation_text))
        score += variables * 0.2
        
        # Pattern bonuses
        if re.search(r'\w+/\w+', equation_text):  # Fractions
            score += 2
        if re.search(r'\w+\^\w+', equation_text):  # Exponents
            score += 2
        if re.search(r'\w+_\w+', equation_text):   # Subscripts
            score += 1
        
        # Length penalties/bonuses
        if len(equation_text) < 10:  # Very short
            score += 1
        elif len(equation_text) > 100:  # Very long
            score -= 1
        
        # Penalties for non-equation content
        false_indicators = ['Figure', 'Table', 'Page', 'Chapter', 'where:', 'Note:']
        for indicator in false_indicators:
            if indicator in equation_text:
                score -= 3
        
        return score
    
    def is_valid_mathematical_equation(self, equation_data):
        """Final validation that this is a mathematical equation"""
        
        # Must have minimum score
        if equation_data['score'] < 3:
            return False
        
        text = equation_data['raw_text']
        
        # Must have mathematical content
        if not (self.has_strong_mathematical_content(text) or 
                (self.has_weak_mathematical_content(text) and len(text) < 50)):
            return False
        
        # Must not be obvious false positives
        false_positive_patterns = [
            r'do not allow transmission',
            r'limit according to',
            r'Steam \d+',
            r'Heat Transfer$',
            r'Babcock.*Wilcox',
            r'^\d+-\d+$'  # Page numbers
        ]
        
        for pattern in false_positive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        return True
    
    def save_bidirectional_equations(self, equations):
        """Save bidirectional extraction results"""
        output_data = {
            "metadata": {
                "document": "Ch-04_Heat_Transfer.pdf",
                "extraction_method": "Bidirectional PyMuPDF (before/after equation numbers)",
                "target_equations": self.target_equation_count,
                "extracted_equations": len(equations),
                "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "success_rate": f"{len(equations)}/{self.target_equation_count} ({len(equations)/self.target_equation_count*100:.1f}%)"
            },
            "statistics": {
                "total_equations": len(equations),
                "equation_numbers": [eq['equation_number'] for eq in equations],
                "direction_analysis": {
                    "before_number": len([eq for eq in equations if eq['direction'] == 'before']),
                    "after_number": len([eq for eq in equations if eq['direction'] == 'after'])
                },
                "score_distribution": {
                    "average_score": sum(eq['score'] for eq in equations) / len(equations) if equations else 0,
                    "score_range": f"{min(eq['score'] for eq in equations):.1f} to {max(eq['score'] for eq in equations):.1f}" if equations else "None"
                }
            },
            "equations": equations
        }
        
        output_path = "bidirectional_equations_corrected.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Bidirectional equations saved: {output_path}")
        return output_path
    
    def run_bidirectional_extraction(self):
        """Run complete bidirectional extraction"""
        print("🚀 Starting bidirectional equation extraction...")
        
        start_time = time.time()
        equations = self.extract_equations_bidirectionally()
        extraction_time = time.time() - start_time
        
        if equations:
            output_path = self.save_bidirectional_equations(equations)
            
            print(f"\n🎉 === BIDIRECTIONAL EXTRACTION COMPLETE ===")
            print(f"⏱️  Extraction time: {extraction_time:.1f}s")
            print(f"📊 Total equations: {len(equations)}")
            
            # Direction analysis
            before_count = len([eq for eq in equations if eq['direction'] == 'before'])
            after_count = len([eq for eq in equations if eq['direction'] == 'after'])
            print(f"📍 Direction distribution:")
            print(f"   🔙 Before number: {before_count} equations")
            print(f"   🔜 After number: {after_count} equations")
            
            # Show sample equations with direction info
            print(f"\n📝 Sample equations with direction analysis:")
            for i, eq in enumerate(equations[:5]):
                direction_symbol = "🔙" if eq['direction'] == 'before' else "🔜"
                print(f"   {i+1}. Eq ({eq['equation_number']}) {direction_symbol} [Score:{eq['score']:.1f}]: {eq['raw_text'][:50]}...")
            
            return output_path
        else:
            print(f"\n❌ No valid equations extracted")
            return None

def main():
    """Main execution with bidirectional approach"""
    extractor = BidirectionalEquationExtractor()
    result = extractor.run_bidirectional_extraction()
    
    if result:
        print(f"\n✅ SUCCESS: Bidirectional equation extraction complete!")
        print(f"📁 Results file: {result}")
        print(f"🔧 Algorithm handles both equation number positions")
        print(f"🔍 Ready for manual validation against PDF content")
    else:
        print(f"\n❌ FAILED: Bidirectional extraction produced no results")

if __name__ == "__main__":
    main()