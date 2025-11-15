#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bibliography Extraction Agent

Extracts bibliographic references from academic documents using GROBID.
Provides structured bibliographic data for citation management and provenance tracking.

Purpose:
    - Extract references section from PDF documents
    - Parse bibliographic metadata (authors, title, journal, year, DOI)
    - Distinguish bibliographic references from internal object references
    - Generate structured bibliography for document packages

GROBID Integration:
    - Uses GROBID REST API (machine learning-based extraction)
    - 87% F1-score on 90,125 reference benchmark
    - Structured XML/TEI output format
    - Installation: Docker-based GROBID service

Architecture:
    - Primary: GROBID REST API for extraction
    - Fallback: PyMuPDF text-based extraction for "References" section
    - Output: Structured JSON bibliography with full metadata

Example Usage:
    >>> agent = BibliographyExtractionAgent(grobid_url="http://localhost:8070")
    >>> references = agent.extract_bibliography(pdf_path)
    >>> print(f"Found {len(references)} bibliographic references")

Author: V12 Development Team
Created: 2025-10-20
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
from dataclasses import dataclass, asdict
import re

# MANDATORY UTF-8 SETUP
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

import fitz  # PyMuPDF
import requests


@dataclass
class BibliographicReference:
    """Structured bibliographic reference."""

    reference_id: str  # e.g., "ref_1", "ref_2"
    raw_text: str  # Original reference text
    authors: List[str]  # List of author names
    title: str  # Article/book title
    journal: Optional[str] = None  # Journal name
    year: Optional[int] = None  # Publication year
    volume: Optional[str] = None  # Volume number
    issue: Optional[str] = None  # Issue number
    pages: Optional[str] = None  # Page range
    doi: Optional[str] = None  # Digital Object Identifier
    url: Optional[str] = None  # Web URL
    publisher: Optional[str] = None  # Publisher name
    extraction_method: str = "grobid"  # grobid, fallback_text, manual


class BibliographyExtractionAgent:
    """
    Extracts bibliographic references from academic documents using GROBID.

    This agent uses GROBID's machine learning-based extraction to parse
    bibliographic references from PDF documents. Falls back to text-based
    extraction if GROBID is unavailable.

    Example:
        >>> agent = BibliographyExtractionAgent(grobid_url="http://localhost:8070")
        >>> references = agent.extract_bibliography("paper.pdf")
        >>> print(f"Found {len(references)} references")
        >>> print(f"First reference: {references[0].title}")
    """

    def __init__(self, grobid_url: str = "http://localhost:8070"):
        """
        Initialize bibliography extraction agent.

        Args:
            grobid_url: URL of GROBID REST service
                       Default: http://localhost:8070 (Docker deployment)
        """
        self.grobid_url = grobid_url
        self.grobid_available = self._check_grobid_availability()

        print("================================================================================")
        print("BIBLIOGRAPHY EXTRACTION AGENT")
        print("================================================================================")
        print(f"GROBID URL: {self.grobid_url}")
        print(f"GROBID Status: {'✅ Available' if self.grobid_available else '❌ Unavailable (using fallback)'}")
        print()

    def _check_grobid_availability(self) -> bool:
        """
        Check if GROBID service is available.

        Returns:
            True if GROBID is responding, False otherwise
        """
        try:
            response = requests.get(f"{self.grobid_url}/api/isalive", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def extract_bibliography(self, pdf_path: Path) -> List[BibliographicReference]:
        """
        Extract bibliographic references from PDF document.

        Args:
            pdf_path: Path to PDF document

        Returns:
            List of BibliographicReference objects
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        print(f"Extracting bibliography from: {pdf_path.name}")
        print()

        if self.grobid_available:
            print("Using GROBID for extraction...")
            references = self._extract_with_grobid(pdf_path)
        else:
            print("⚠️  GROBID unavailable, using fallback text extraction...")
            references = self._extract_with_fallback(pdf_path)

        print(f"✅ Extracted {len(references)} bibliographic references")
        print()

        return references

    def _extract_with_grobid(self, pdf_path: Path) -> List[BibliographicReference]:
        """
        Extract bibliography using GROBID REST API.

        Args:
            pdf_path: Path to PDF document

        Returns:
            List of BibliographicReference objects
        """
        # Call GROBID processReferences endpoint
        url = f"{self.grobid_url}/api/processReferences"

        with pdf_path.open('rb') as f:
            files = {'input': f}
            response = requests.post(url, files=files, timeout=300)

        if response.status_code != 200:
            print(f"⚠️  GROBID request failed with status {response.status_code}")
            print("Falling back to text extraction...")
            return self._extract_with_fallback(pdf_path)

        # Parse GROBID XML/TEI output
        references = self._parse_grobid_response(response.text)

        return references

    def _parse_grobid_response(self, xml_text: str) -> List[BibliographicReference]:
        """
        Parse GROBID XML/TEI response.

        Args:
            xml_text: XML response from GROBID

        Returns:
            List of BibliographicReference objects
        """
        # Parse XML using ElementTree
        import xml.etree.ElementTree as ET

        references = []

        try:
            root = ET.fromstring(xml_text)

            # GROBID uses TEI namespace
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

            # Find all biblStruct elements (bibliographic references)
            for i, biblio in enumerate(root.findall('.//tei:biblStruct', ns), 1):
                ref = self._parse_biblio_struct(biblio, i, ns)
                references.append(ref)

        except ET.ParseError as e:
            print(f"⚠️  XML parsing error: {e}")
            # Return empty list if parsing fails
            return []

        return references

    def _parse_biblio_struct(self, biblio: Any, ref_num: int, ns: Dict[str, str]) -> BibliographicReference:
        """
        Parse a single biblStruct element from GROBID XML.

        Args:
            biblio: XML element (biblStruct)
            ref_num: Reference number
            ns: XML namespaces

        Returns:
            BibliographicReference object
        """
        # Extract authors
        authors = []
        for author in biblio.findall('.//tei:author/tei:persName', ns):
            forename = author.find('tei:forename', ns)
            surname = author.find('tei:surname', ns)

            forename_text = forename.text if forename is not None else ""
            surname_text = surname.text if surname is not None else ""

            if surname_text:
                authors.append(f"{forename_text} {surname_text}".strip())

        # Extract title
        title_elem = biblio.find('.//tei:title[@level="a"]', ns)
        title = title_elem.text if title_elem is not None else "Unknown Title"

        # Extract journal
        journal_elem = biblio.find('.//tei:title[@level="j"]', ns)
        journal = journal_elem.text if journal_elem is not None else None

        # Extract year
        year = None
        date_elem = biblio.find('.//tei:date[@type="published"]', ns)
        if date_elem is not None and 'when' in date_elem.attrib:
            try:
                year = int(date_elem.attrib['when'][:4])  # Extract year from YYYY-MM-DD
            except (ValueError, IndexError):
                pass

        # Extract volume and issue
        volume_elem = biblio.find('.//tei:biblScope[@unit="volume"]', ns)
        volume = volume_elem.text if volume_elem is not None else None

        issue_elem = biblio.find('.//tei:biblScope[@unit="issue"]', ns)
        issue = issue_elem.text if issue_elem is not None else None

        # Extract page range
        pages_elem = biblio.find('.//tei:biblScope[@unit="page"]', ns)
        pages = None
        if pages_elem is not None:
            from_page = pages_elem.attrib.get('from', '')
            to_page = pages_elem.attrib.get('to', '')
            if from_page and to_page:
                pages = f"{from_page}-{to_page}"
            elif from_page:
                pages = from_page

        # Extract DOI
        doi_elem = biblio.find('.//tei:idno[@type="DOI"]', ns)
        doi = doi_elem.text if doi_elem is not None else None

        # Get raw text (approximation)
        raw_text = self._biblio_to_text(authors, title, journal, year, volume, issue, pages)

        return BibliographicReference(
            reference_id=f"ref_{ref_num}",
            raw_text=raw_text,
            authors=authors,
            title=title,
            journal=journal,
            year=year,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            extraction_method="grobid"
        )

    def _biblio_to_text(
        self,
        authors: List[str],
        title: str,
        journal: Optional[str],
        year: Optional[int],
        volume: Optional[str],
        issue: Optional[str],
        pages: Optional[str]
    ) -> str:
        """
        Convert bibliographic fields to formatted citation text.

        Args:
            authors: List of author names
            title: Article title
            journal: Journal name
            year: Publication year
            volume: Volume number
            issue: Issue number
            pages: Page range

        Returns:
            Formatted citation string
        """
        parts = []

        # Authors
        if authors:
            if len(authors) == 1:
                parts.append(authors[0])
            elif len(authors) == 2:
                parts.append(f"{authors[0]} and {authors[1]}")
            else:
                parts.append(f"{authors[0]} et al.")

        # Year
        if year:
            parts.append(f"({year})")

        # Title
        parts.append(f'"{title}"')

        # Journal info
        journal_parts = []
        if journal:
            journal_parts.append(journal)
        if volume:
            journal_parts.append(f"vol. {volume}")
        if issue:
            journal_parts.append(f"no. {issue}")
        if pages:
            journal_parts.append(f"pp. {pages}")

        if journal_parts:
            parts.append(", ".join(journal_parts))

        return ". ".join(parts) + "."

    def _extract_with_fallback(self, pdf_path: Path) -> List[BibliographicReference]:
        """
        Fallback extraction using PyMuPDF text extraction.

        Searches for "References" section and extracts reference list.

        Args:
            pdf_path: Path to PDF document

        Returns:
            List of BibliographicReference objects
        """
        doc = fitz.open(str(pdf_path))
        references = []

        # Search for "References" section
        refs_page = None
        refs_start_y = None

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            # Look for "References" or "REFERENCES" as standalone heading
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if re.match(r'^\s*REFERENCES?\s*$', line, re.IGNORECASE):
                    refs_page = page_num
                    # Get approximate Y position by searching text blocks
                    blocks = page.get_text("blocks")
                    for block in blocks:
                        if "REFERENCES" in block[4].upper():
                            refs_start_y = block[1]  # Y0 coordinate
                            break
                    break

            if refs_page is not None:
                break

        if refs_page is None:
            print("⚠️  'References' section not found in document")
            doc.close()
            return []

        # Extract references text from References section
        refs_text_lines = []

        for page_num in range(refs_page, len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")

            for block in blocks:
                x0, y0, x1, y1, text, block_no, block_type = block

                # Skip headers and footers (approximate)
                if y0 < 50 or y0 > page.rect.height - 50:
                    continue

                # On first page, skip until we reach references heading
                if page_num == refs_page and refs_start_y is not None:
                    if y0 < refs_start_y:
                        continue

                refs_text_lines.append(text.strip())

        refs_text = "\n".join(refs_text_lines)

        # Parse references using simple heuristics
        # Look for numbered references like [1], [2], (1), (2), or 1., 2.
        ref_pattern = r'(?:^\[(\d+)\]|^\((\d+)\)|^(\d+)\.)\s+'

        current_ref_num = None
        current_ref_text = []

        for line in refs_text.split('\n'):
            match = re.match(ref_pattern, line)

            if match:
                # Save previous reference
                if current_ref_num and current_ref_text:
                    ref = self._parse_fallback_reference(current_ref_num, " ".join(current_ref_text))
                    references.append(ref)

                # Start new reference
                current_ref_num = match.group(1) or match.group(2) or match.group(3)
                current_ref_text = [re.sub(ref_pattern, '', line).strip()]
            else:
                # Continue current reference
                if line.strip():
                    current_ref_text.append(line.strip())

        # Save last reference
        if current_ref_num and current_ref_text:
            ref = self._parse_fallback_reference(current_ref_num, " ".join(current_ref_text))
            references.append(ref)

        doc.close()
        return references

    def _parse_fallback_reference(self, ref_num: str, text: str) -> BibliographicReference:
        """
        Parse reference using basic heuristics (fallback method).

        Args:
            ref_num: Reference number
            text: Reference text

        Returns:
            BibliographicReference with basic parsing
        """
        # Very basic parsing - just extract year with regex
        year = None
        year_match = re.search(r'\((\d{4})\)', text)
        if year_match:
            year = int(year_match.group(1))

        # Extract authors (assume first part before year or comma)
        authors = []
        if '(' in text:
            author_text = text.split('(')[0].strip()
            if ',' in author_text:
                authors = [author_text.split(',')[0].strip()]
        elif ',' in text:
            authors = [text.split(',')[0].strip()]

        return BibliographicReference(
            reference_id=f"ref_{ref_num}",
            raw_text=text,
            authors=authors if authors else ["Unknown Author"],
            title="Unknown Title",  # Requires more sophisticated parsing
            year=year,
            extraction_method="fallback_text"
        )

    def save_bibliography(
        self,
        references: List[BibliographicReference],
        output_path: Path
    ) -> None:
        """
        Save bibliography to JSON file.

        Args:
            references: List of BibliographicReference objects
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        output_data = {
            "extraction_timestamp": datetime.now().isoformat(),
            "reference_count": len(references),
            "references": []
        }

        for ref in references:
            output_data["references"].append({
                "reference_id": ref.reference_id,
                "raw_text": ref.raw_text,
                "authors": ref.authors,
                "title": ref.title,
                "journal": ref.journal,
                "year": ref.year,
                "volume": ref.volume,
                "issue": ref.issue,
                "pages": ref.pages,
                "doi": ref.doi,
                "url": ref.url,
                "publisher": ref.publisher,
                "extraction_method": ref.extraction_method
            })

        with output_path.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved bibliography to: {output_path}")

        # Also generate human-readable text format
        txt_path = output_path.with_suffix('.txt')
        with txt_path.open('w', encoding='utf-8') as f:
            f.write('=' * 80 + '\n')
            f.write('BIBLIOGRAPHY - Chapter 4 Heat Transfer\n')
            f.write('=' * 80 + '\n')
            f.write(f'\n')
            f.write(f'Extracted: {output_data["extraction_timestamp"]}\n')
            f.write(f'Total References: {output_data["reference_count"]}\n')
            f.write('\n')
            f.write('=' * 80 + '\n')
            f.write('\n')
            for ref in output_data['references']:
                ref_num = ref['reference_id'].replace('ref_', '')
                f.write(f'[{ref_num}] {ref["raw_text"]}\n\n')

        print(f"✅ Saved text bibliography to: {txt_path}")

        # Also generate markdown format
        md_path = output_path.with_suffix('.md')
        with md_path.open('w', encoding='utf-8') as f:
            f.write('# Bibliography - Chapter 4 Heat Transfer\n\n')
            f.write(f'**Extracted**: {output_data["extraction_timestamp"]}  \n')
            f.write(f'**Total References**: {output_data["reference_count"]}\n\n')
            f.write('---\n\n')
            for ref in output_data['references']:
                ref_num = ref['reference_id'].replace('ref_', '')
                f.write(f'**[{ref_num}]** {ref["raw_text"]}\n\n')

        print(f"✅ Saved markdown bibliography to: {md_path}")


if __name__ == "__main__":
    # Test on Chapter 4
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found: {pdf_path}")
        sys.exit(1)

    # Initialize agent (will use fallback if GROBID not available)
    agent = BibliographyExtractionAgent(grobid_url="http://localhost:8070")

    # Extract bibliography
    references = agent.extract_bibliography(pdf_path)

    # Save results
    output_path = Path("results/bibliography/bibliography.json")
    agent.save_bibliography(references, output_path)

    print("\n=== BIBLIOGRAPHY SUMMARY ===")
    print(f"Total references: {len(references)}")
    print(f"\nFirst 3 references:")
    for ref in references[:3]:
        print(f"\n  [{ref.reference_id}]")
        print(f"    Authors: {', '.join(ref.authors)}")
        print(f"    Title: {ref.title}")
        if ref.journal:
            print(f"    Journal: {ref.journal}")
        if ref.year:
            print(f"    Year: {ref.year}")
        print(f"    Method: {ref.extraction_method}")
