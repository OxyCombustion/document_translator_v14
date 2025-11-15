#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Citation Extraction Agent - Cross-Reference Post-Processing

This agent extracts and maps citations from text chunks to target objects
(equations, tables, figures). It operates as a post-processing step after
all content extraction is complete, building bidirectional references.

Design Rationale:
-----------------
- **Post-Processing**: Citations are cross-cutting concerns that reference multiple types
- **Bidirectional**: Updates both source (text) and target (object) references
- **Graph Building**: Creates citation edges for cross-reference graph
- **Context Preservation**: Maintains full sentence and surrounding text

Author: Claude Opus 4.1
Date: 2025-10-08
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re
import json
from datetime import datetime
from dataclasses import dataclass, asdict

# MANDATORY UTF-8 SETUP - NO EXCEPTIONS
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

# Import base structures
from base_extraction_agent import ExtractedObject


@dataclass
class Citation:
    """
    Represents a single citation of an object in text.

    Attributes:
        object_type: Type of object ('figure', 'table', 'equation')
        object_id: ID of target object ('fig_1', 'table_2', 'eq_5')
        source_id: ID of source text chunk containing citation
        page: Page number where citation appears
        text_before: Context before citation (100 chars)
        citation_text: The actual citation phrase
        text_after: Context after citation (100 chars)
        sentence: Full sentence containing citation
    """
    object_type: str
    object_id: str
    source_id: str
    page: int
    text_before: str
    citation_text: str
    text_after: str
    sentence: str


class CitationExtractionAgent:
    """
    Post-processing agent that extracts and maps object citations.

    This agent operates on already-extracted objects to:
    1. Find all citations in text chunks
    2. Map citations to target objects
    3. Update ExtractedObject.references bidirectionally
    4. Generate citation statistics and reports

    Usage Example:
    --------------
    >>> agent = CitationExtractionAgent()
    >>> updated_objects = agent.process_extractions(
    ...     equations=equations_list,
    ...     tables=tables_list,
    ...     figures=figures_list,
    ...     text_chunks=text_list
    ... )
    """

    def __init__(self):
        """Initialize citation extraction agent."""
        self.agent_type = "citation_extraction"
        self.agent_version = "1.0.0"

        # Citation patterns (proven from Phase 1 with 386 citations found)
        self.patterns = {
            'figure': [
                r'(?i)(?:fig\.|figure|figs\.|figures)\s+(\d+[a-z]?)',
                r'(?i)(?:see|shown in|illustrated in|depicted in)\s+(?:fig\.|figure)\s+(\d+[a-z]?)',
            ],
            'table': [
                r'(?i)(?:table|tables)\s+(\d+[a-z]?)',
                r'(?i)(?:see|shown in|listed in|given in)\s+table\s+(\d+[a-z]?)',
            ],
            'equation': [
                r'(?i)(?:eq\.|equation|eqs\.|equations)\s+(\d+[a-z]?)',
                r'(?i)(?:using|from|by)\s+(?:eq\.|equation)\s+(\d+[a-z]?)',
                r'\((\d+[a-z]?)\)',  # Equation numbers in parentheses
            ]
        }

        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for obj_type, pattern_list in self.patterns.items():
            self.compiled_patterns[obj_type] = [
                re.compile(pattern) for pattern in pattern_list
            ]

        # Statistics
        self.stats = {
            'total_citations': 0,
            'figure_citations': 0,
            'table_citations': 0,
            'equation_citations': 0,
            'text_chunks_processed': 0,
            'objects_with_citations': 0
        }

    def _get_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """
        Safely get attribute from both dict and object formats.

        Args:
            obj: Dict or object instance
            attr: Attribute name
            default: Default value if attribute not found

        Returns:
            Attribute value or default
        """
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def _set_attr(self, obj: Any, attr: str, value: Any) -> None:
        """
        Safely set attribute for both dict and object formats.

        Args:
            obj: Dict or object instance
            attr: Attribute name
            value: Value to set
        """
        if isinstance(obj, dict):
            obj[attr] = value
        else:
            setattr(obj, attr, value)

    def process_extractions(
        self,
        equations: List[ExtractedObject],
        tables: List[ExtractedObject],
        figures: List[ExtractedObject],
        text_chunks: List[ExtractedObject]
    ) -> Dict[str, List[ExtractedObject]]:
        """
        Main entry point - processes all extracted objects to find and map citations.

        Args:
            equations: List of extracted equation objects
            tables: List of extracted table objects
            figures: List of extracted figure objects
            text_chunks: List of extracted text chunk objects

        Returns:
            Dictionary with updated objects including bidirectional references
        """
        print("="*70)
        print("CITATION EXTRACTION")
        print("="*70)
        print(f"Processing citations from {len(text_chunks)} text chunks...")

        # Create object lookup dictionary for fast access
        all_objects = {}
        for obj in equations + tables + figures:
            # Handle both dict and object formats
            obj_id = obj['id'] if isinstance(obj, dict) else obj.id
            # Store by both full ID and number
            all_objects[obj_id] = obj
            # Also store by type_number format for flexible matching
            if '_' in obj_id:
                obj_type, obj_num = obj_id.rsplit('_', 1)
                all_objects[f"{obj_type}_{obj_num}"] = obj

        # Extract citations from each text chunk
        all_citations = []
        for text_obj in text_chunks:
            self.stats['text_chunks_processed'] += 1
            citations = self._extract_citations_from_text(text_obj)
            all_citations.extend(citations)

        print(f"  Found {len(all_citations)} total citations")

        # Map citations to objects and update references bidirectionally
        citation_map = {}
        for citation in all_citations:
            target_obj = self._map_citation_to_object(citation, all_objects)
            if target_obj:
                # Update bidirectional references
                self._update_references_bidirectionally(
                    citation, text_chunks, target_obj
                )

                # Track citation statistics
                if citation.object_id not in citation_map:
                    citation_map[citation.object_id] = []
                citation_map[citation.object_id].append(citation)

        # Update statistics
        self._update_statistics(all_citations, citation_map)

        # Print summary
        self._print_summary(citation_map)

        # Return updated objects
        return {
            'equations': equations,
            'tables': tables,
            'figures': figures,
            'text': text_chunks
        }

    def _extract_citations_from_text(self, text_obj: ExtractedObject) -> List[Citation]:
        """
        Extract citations from a text chunk using proven regex patterns.

        Args:
            text_obj: Text chunk ExtractedObject

        Returns:
            List of Citation objects found in the text
        """
        citations = []

        # Get text content
        content = self._get_attr(text_obj, 'content', {})
        if isinstance(content, dict):
            text_content = content.get('text', '')
        elif isinstance(content, str):
            text_content = content
        else:
            text_content = ""

        if not text_content:
            return citations

        # Search for each pattern type
        for obj_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text_content)

                for match in matches:
                    # Extract object number
                    if match.groups():
                        obj_num = match.group(1)
                    else:
                        continue

                    # Get context (100 chars before/after)
                    start = max(0, match.start() - 100)
                    end = min(len(text_content), match.end() + 100)

                    text_before = text_content[start:match.start()].strip()
                    citation_text = match.group(0)
                    text_after = text_content[match.end():end].strip()

                    # Extract full sentence
                    sentence = self._extract_sentence(text_content, match.start(), match.end())

                    # Create citation
                    citation = Citation(
                        object_type=obj_type,
                        object_id=f"{obj_type}_{obj_num}",
                        source_id=self._get_attr(text_obj, 'id', 'unknown'),
                        page=self._get_attr(text_obj, 'page', 0),
                        text_before=text_before[-100:],
                        citation_text=citation_text,
                        text_after=text_after[:100],
                        sentence=sentence
                    )

                    citations.append(citation)
                    self.stats[f'{obj_type}_citations'] += 1
                    self.stats['total_citations'] += 1

        return citations

    def _extract_sentence(self, text: str, start: int, end: int) -> str:
        """
        Extract the full sentence containing the citation.

        Args:
            text: Full text content
            start: Start position of citation
            end: End position of citation

        Returns:
            Full sentence containing the citation
        """
        # Find sentence boundaries (. ! ?)
        sentence_start = start
        sentence_end = end

        # Search backward for sentence start
        for i in range(start - 1, max(0, start - 500), -1):
            if text[i] in '.!?\n' and i > 0:
                sentence_start = i + 1
                break

        # Search forward for sentence end
        for i in range(end, min(len(text), end + 500)):
            if text[i] in '.!?':
                sentence_end = i + 1
                break

        sentence = text[sentence_start:sentence_end].strip()
        return sentence

    def _map_citation_to_object(
        self, citation: Citation, all_objects: Dict[str, ExtractedObject]
    ) -> Optional[ExtractedObject]:
        """
        Map a citation to its target object.

        Args:
            citation: Citation to map
            all_objects: Dictionary of all extracted objects

        Returns:
            Target ExtractedObject if found, None otherwise
        """
        # Try direct lookup
        if citation.object_id in all_objects:
            return all_objects[citation.object_id]

        # Try variations (e.g., 'eq_1' vs 'equation_1')
        variations = [
            citation.object_id,
            citation.object_id.replace('eq_', 'equation_'),
            citation.object_id.replace('fig_', 'figure_'),
            f"{citation.object_type}_{citation.object_id.split('_')[-1]}"
        ]

        for variant in variations:
            if variant in all_objects:
                return all_objects[variant]

        # Not found
        print(f"  ⚠️  Could not map citation: {citation.object_id}")
        return None

    def _update_references_bidirectionally(
        self,
        citation: Citation,
        text_chunks: List[ExtractedObject],
        target_obj: ExtractedObject
    ):
        """
        Update references in both source and target objects.

        Args:
            citation: Citation linking source to target
            text_chunks: List of text chunks to find source
            target_obj: Target object being cited
        """
        # Find source text chunk
        source_obj = None
        for text_obj in text_chunks:
            if self._get_attr(text_obj, 'id') == citation.source_id:
                source_obj = text_obj
                break

        if not source_obj:
            return

        # Get references for source and target
        source_refs = self._get_attr(source_obj, 'references', {})
        target_refs = self._get_attr(target_obj, 'references', {})

        # Ensure references dicts exist
        if not source_refs:
            source_refs = {}
            self._set_attr(source_obj, 'references', source_refs)
        if not target_refs:
            target_refs = {}
            self._set_attr(target_obj, 'references', target_refs)

        # Update source object (text chunk) - outgoing references
        if 'cites' not in source_refs:
            source_refs['cites'] = []
        target_id = self._get_attr(target_obj, 'id')
        if target_id not in source_refs['cites']:
            source_refs['cites'].append(target_id)

        # Update target object - incoming references
        if 'cited_by' not in target_refs:
            target_refs['cited_by'] = []
        source_id = self._get_attr(source_obj, 'id')
        if source_id not in target_refs['cited_by']:
            target_refs['cited_by'].append(source_id)

        # Add citation context to target
        if 'citation_contexts' not in target_refs:
            target_refs['citation_contexts'] = []

        target_refs['citation_contexts'].append({
            'source_id': source_id,
            'page': citation.page,
            'sentence': citation.sentence,
            'citation_text': citation.citation_text
        })

        # Update citation count
        if 'citation_count' not in target_refs:
            target_refs['citation_count'] = 0
        target_refs['citation_count'] += 1

        # Track pages where mentioned
        if 'mentioned_on_pages' not in target_refs:
            target_refs['mentioned_on_pages'] = []
        if citation.page not in target_refs['mentioned_on_pages']:
            target_refs['mentioned_on_pages'].append(citation.page)

    def _update_statistics(
        self,
        all_citations: List[Citation],
        citation_map: Dict[str, List[Citation]]
    ):
        """Update agent statistics."""
        self.stats['objects_with_citations'] = len(citation_map)

    def _print_summary(self, citation_map: Dict[str, List[Citation]]):
        """Print extraction summary."""
        print("\n" + "-"*70)
        print("CITATION EXTRACTION SUMMARY")
        print("-"*70)
        print(f"  Total citations: {self.stats['total_citations']}")
        print(f"  Figure citations: {self.stats['figure_citations']}")
        print(f"  Table citations: {self.stats['table_citations']}")
        print(f"  Equation citations: {self.stats['equation_citations']}")
        print(f"  Text chunks processed: {self.stats['text_chunks_processed']}")
        print(f"  Objects with citations: {self.stats['objects_with_citations']}")

        # Show most cited objects
        if citation_map:
            print("\n  Most cited objects:")
            sorted_objs = sorted(
                citation_map.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:5]

            for obj_id, citations in sorted_objs:
                pages = sorted(set(c.page for c in citations))
                print(f"    {obj_id}: {len(citations)} citations on pages {pages}")

        print("="*70)

    def generate_report(self, output_path: Path) -> Dict[str, Any]:
        """
        Generate detailed citation report.

        Args:
            output_path: Path to save report

        Returns:
            Report dictionary with statistics and citation details
        """
        report = {
            'metadata': {
                'agent_type': self.agent_type,
                'agent_version': self.agent_version,
                'extraction_date': datetime.now().isoformat()
            },
            'statistics': self.stats,
            'citations': []  # Would be populated with detailed citation data
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"  💾 Citation report saved: {output_path}")
        return report