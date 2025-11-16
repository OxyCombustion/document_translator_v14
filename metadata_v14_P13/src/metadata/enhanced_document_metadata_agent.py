#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Document Metadata Agent with Impact Assessment

Extends DocumentMetadataAgent to include impact assessment metrics
for evaluating document reliability and importance.

Features:
- All original metadata extraction capabilities
- Impact assessment integration
- Citation graph analysis
- Open access status checking
- Composite impact scoring
- Visualization dashboard data generation

Author: Claude Code
Date: 2025-10-13
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime
import logging

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

# Import base agent and impact assessment components
from .document_metadata_agent import DocumentMetadataAgent
from .impact_assessment_agent import ImpactAssessmentAgent, ImpactComponents
from .citation_graph_analyzer import CitationGraphAnalyzer

# Import API clients
from openalex_client import OpenAlexClient
from crossref_client import CrossrefClient
from unpaywall_client import UnpaywallClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedDocumentMetadataAgent(DocumentMetadataAgent):
    """
    Enhanced metadata agent with impact assessment.

    Combines traditional metadata extraction with impact scoring
    to provide comprehensive document reliability assessment.
    """

    def __init__(
        self,
        output_dir: Path,
        zotero_agent=None,
        email: str = "test@example.com",
        enable_impact: bool = True,
        cache_dir: Path = None
    ):
        """
        Initialize enhanced metadata agent.

        Args:
            output_dir: Directory for metadata cache
            zotero_agent: Optional ZoteroIntegrationAgent instance
            email: Email for API polite pools
            enable_impact: Whether to enable impact assessment
            cache_dir: Directory for API response caching
        """
        # Initialize base agent
        super().__init__(output_dir, zotero_agent)

        self.enable_impact = enable_impact
        self.email = email
        self.cache_dir = Path(cache_dir or "cache")

        if self.enable_impact:
            # Initialize impact assessment
            self.impact_agent = ImpactAssessmentAgent(
                cache_dir=self.cache_dir / "impact"
            )

            # Initialize API clients
            self.openalex = OpenAlexClient(
                email=email,
                cache_dir=self.cache_dir / "openalex"
            )

            self.crossref = CrossrefClient(
                email=email,
                cache_dir=self.cache_dir / "crossref"
            )

            self.unpaywall = UnpaywallClient(
                email=email,
                cache_dir=self.cache_dir / "unpaywall"
            )

            # Initialize citation graph
            self.citation_graph = CitationGraphAnalyzer(
                db_path=self.cache_dir / "citation_graph.db"
            )

        # Enhanced cache file
        self.enhanced_cache_file = self.output_dir / "enhanced_document_metadata.json"

    def get_or_extract_metadata(
        self,
        pdf_path: Path,
        include_impact: bool = True
    ) -> Dict[str, Any]:
        """
        Get metadata with optional impact assessment.

        Args:
            pdf_path: Path to PDF file
            include_impact: Whether to include impact metrics

        Returns:
            Complete metadata with impact assessment
        """
        # Get base metadata
        metadata = super().get_or_extract_metadata(pdf_path)

        # Add impact assessment if enabled
        if self.enable_impact and include_impact:
            # Check enhanced cache first
            fingerprint = self._get_document_fingerprint(pdf_path)
            cached_enhanced = self._load_enhanced_cache()

            if cached_enhanced and cached_enhanced.get('fingerprint') == fingerprint:
                logger.info("Using cached enhanced metadata with impact")
                return cached_enhanced

            # Calculate impact
            logger.info("Calculating impact assessment...")
            impact_data = self._calculate_impact(metadata)
            metadata['impact'] = impact_data

            # Add to citation graph
            self._update_citation_graph(metadata)

            # Save to enhanced cache
            metadata['fingerprint'] = fingerprint
            self._save_enhanced_cache(metadata)

        return metadata

    def _calculate_impact(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate impact assessment for document.

        Args:
            metadata: Basic document metadata

        Returns:
            Impact assessment data
        """
        impact_data = {
            'calculated_at': datetime.now().isoformat(),
            'components': {},
            'composite_score': 0.0,
            'reliability_level': 'unknown'
        }

        # Get DOI for API lookups
        doi = metadata.get('doi')

        # 1. Citation metrics from OpenAlex
        if doi:
            logger.info(f"Fetching citation data for DOI: {doi}")
            openalex_data = self.openalex.get_work_by_doi(doi)

            if openalex_data:
                citation_metrics = self.openalex.extract_citation_metrics(openalex_data)
                impact_data['components']['citations'] = citation_metrics

                # Field-normalized citations
                field_norm = self.openalex.calculate_field_normalized_citations(
                    citation_metrics['citations_count'],
                    citation_metrics.get('field_citation_mean', 1)
                )
                impact_data['components']['field_normalized_citations'] = field_norm

        # 2. Venue metrics from Crossref
        if doi:
            logger.info(f"Fetching bibliographic data for DOI: {doi}")
            crossref_data = self.crossref.get_work(doi)

            if crossref_data:
                impact_metrics = self.crossref.extract_impact_metrics(crossref_data)
                impact_data['components']['bibliographic'] = impact_metrics

                # Check OA status from Crossref
                oa_status = self.crossref.check_oa_status(crossref_data)
                impact_data['components']['oa_crossref'] = oa_status

        # 3. Open Access status from Unpaywall
        if doi:
            logger.info(f"Fetching OA status for DOI: {doi}")
            unpaywall_data = self.unpaywall.get_oa_status(doi)

            if unpaywall_data:
                oa_metrics = self.unpaywall.extract_oa_metrics(unpaywall_data)
                impact_data['components']['open_access'] = oa_metrics

                # OA quality score
                oa_score = self.unpaywall.get_oa_score(oa_metrics)
                impact_data['components']['oa_score'] = oa_score

        # 4. Internal citation graph metrics
        doc_id = metadata.get('document_id', metadata.get('pdf_filename', 'unknown'))
        graph_metrics = self.citation_graph.get_document_importance(doc_id)

        if graph_metrics:
            impact_data['components']['internal_graph'] = graph_metrics

        # 5. Extract quality metrics (if available)
        extraction_quality = metadata.get('extraction_quality', {})
        if extraction_quality:
            impact_data['components']['extraction_quality'] = extraction_quality

        # 6. Calculate composite score
        composite_score, reliability_level = self._calculate_composite_score(impact_data['components'])
        impact_data['composite_score'] = composite_score
        impact_data['reliability_level'] = reliability_level

        # 7. Generate recommendations
        recommendations = self._generate_recommendations(impact_data)
        impact_data['recommendations'] = recommendations

        return impact_data

    def _calculate_composite_score(
        self,
        components: Dict[str, Any]
    ) -> Tuple[float, str]:
        """
        Calculate composite impact score and reliability level.

        Args:
            components: Individual impact components

        Returns:
            (composite_score, reliability_level)
        """
        # Extract individual scores
        citation_score = 0.0
        venue_score = 0.0
        oa_score = components.get('oa_score', 0.0)
        internal_score = 0.0
        extraction_score = 0.0

        # Citation score (normalized 0-1)
        if 'citations' in components:
            citations = components['citations'].get('citations_count', 0)
            # Logarithmic scaling for citations
            if citations > 0:
                import math
                citation_score = min(1.0, math.log10(citations + 1) / 3)  # 1000 citations = 1.0

        # Field-normalized citation bonus
        if 'field_normalized_citations' in components:
            field_norm = components['field_normalized_citations']
            if field_norm > 1.0:
                citation_score = min(1.0, citation_score * (1 + (field_norm - 1) * 0.1))

        # Venue score from journal metrics
        if 'bibliographic' in components:
            bib = components['bibliographic']
            venue_components = []

            # Publisher reputation (simplified)
            if bib.get('publisher', {}).get('name'):
                publisher = bib['publisher']['name'].lower()
                if any(p in publisher for p in ['nature', 'science', 'elsevier', 'springer', 'wiley']):
                    venue_components.append(0.8)

            # References indicate quality
            if bib.get('references', {}).get('count', 0) > 20:
                venue_components.append(0.7)

            venue_score = max(venue_components) if venue_components else 0.3

        # Internal graph importance
        if 'internal_graph' in components:
            graph = components['internal_graph']
            # Use PageRank as primary internal importance
            internal_score = min(1.0, graph.get('pagerank', 0.0) * 100)  # Scale PageRank

        # Extraction quality
        if 'extraction_quality' in components:
            quality = components['extraction_quality']
            extraction_score = quality.get('overall_score', 0.5)

        # Create impact components for scoring
        impact_components = ImpactComponents(
            field_norm_citations=citation_score,
            venue_prestige=venue_score,
            author_influence=0.5,  # Default if not available
            recency=0.7,  # Default, could calculate from year
            openaccess=oa_score,
            altmetrics=0.0,  # Not implemented yet
            internal_usage=internal_score,
            content_quality=extraction_score
        )

        # Calculate composite score
        composite = self.impact_agent.calculate_composite_score(impact_components)

        # Determine reliability level
        if composite >= 0.8:
            reliability = "very_high"
        elif composite >= 0.6:
            reliability = "high"
        elif composite >= 0.4:
            reliability = "moderate"
        elif composite >= 0.2:
            reliability = "low"
        else:
            reliability = "very_low"

        return composite, reliability

    def _update_citation_graph(self, metadata: Dict[str, Any]):
        """
        Add document and its citations to internal graph.

        Args:
            metadata: Document metadata with citations
        """
        doc_id = metadata.get('document_id', metadata.get('pdf_filename', 'unknown'))

        # Add document to graph
        self.citation_graph.add_document(
            doc_id=doc_id,
            title=metadata.get('title', metadata.get('chapter_title', 'Unknown')),
            doi=metadata.get('doi'),
            year=metadata.get('year'),
            authors=metadata.get('authors', []),
            venue=metadata.get('publication', metadata.get('book_title')),
            extracted=True,
            metadata=metadata
        )

        # Add citations if available
        if 'citations' in metadata:
            self.citation_graph.add_citations_from_extraction(
                doc_id=doc_id,
                extracted_citations=metadata['citations']
            )

    def _generate_recommendations(self, impact_data: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on impact assessment.

        Args:
            impact_data: Calculated impact data

        Returns:
            List of recommendation strings
        """
        recommendations = []
        components = impact_data.get('components', {})

        # Low citations
        if 'citations' in components:
            citations = components['citations'].get('citations_count', 0)
            if citations < 10:
                recommendations.append(
                    "Document has low citation count - verify findings with additional sources"
                )

        # No open access
        if 'open_access' in components:
            if not components['open_access'].get('is_oa', False):
                recommendations.append(
                    "Document is not open access - consider accessibility for readers"
                )

        # Low extraction quality
        if 'extraction_quality' in components:
            if components['extraction_quality'].get('overall_score', 1.0) < 0.5:
                recommendations.append(
                    "Extraction quality is low - manual verification recommended"
                )

        # High internal importance
        if 'internal_graph' in components:
            if components['internal_graph'].get('pagerank', 0) > 0.1:
                recommendations.append(
                    "Document is highly referenced internally - key resource"
                )

        # Overall reliability
        reliability = impact_data.get('reliability_level', 'unknown')
        if reliability in ['low', 'very_low']:
            recommendations.append(
                "Overall reliability is low - use with caution and cross-reference"
            )
        elif reliability in ['very_high']:
            recommendations.append(
                "High reliability document - suitable as primary source"
            )

        return recommendations

    def _load_enhanced_cache(self) -> Optional[Dict[str, Any]]:
        """Load enhanced cached metadata if exists."""
        if not self.enhanced_cache_file.exists():
            return None

        try:
            with open(self.enhanced_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Enhanced cache load failed: {e}")
            return None

    def _save_enhanced_cache(self, metadata: Dict[str, Any]):
        """Save enhanced metadata to cache."""
        try:
            with open(self.enhanced_cache_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Enhanced metadata cached to: {self.enhanced_cache_file}")
        except Exception as e:
            logger.error(f"Enhanced cache save failed: {e}")

    def generate_impact_report(
        self,
        metadata: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate human-readable impact assessment report.

        Args:
            metadata: Enhanced metadata with impact
            output_path: Optional path to save report

        Returns:
            Report as markdown string
        """
        report = []
        report.append("# Document Impact Assessment Report\n")
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Document info
        report.append("## Document Information\n")
        report.append(f"- **Title**: {metadata.get('title', 'Unknown')}")
        report.append(f"- **Authors**: {', '.join(metadata.get('authors', ['Unknown']))}")
        report.append(f"- **Year**: {metadata.get('year', 'Unknown')}")
        report.append(f"- **DOI**: {metadata.get('doi', 'N/A')}")
        report.append(f"- **Type**: {metadata.get('document_type', 'Unknown')}\n")

        # Impact assessment
        if 'impact' in metadata:
            impact = metadata['impact']

            report.append("## Impact Assessment\n")
            report.append(f"### Overall Score: {impact['composite_score']:.2f}/1.00")
            report.append(f"### Reliability Level: **{impact['reliability_level'].upper()}**\n")

            # Component scores
            report.append("### Component Scores\n")
            components = impact.get('components', {})

            # Citations
            if 'citations' in components:
                cit = components['citations']
                report.append(f"#### Citations")
                report.append(f"- Total Citations: {cit.get('citations_count', 0)}")
                report.append(f"- Citations per Year: {cit.get('citations_per_year', 0):.1f}")
                report.append(f"- h-index: {cit.get('h_index', 'N/A')}")

            # Open Access
            if 'open_access' in components:
                oa = components['open_access']
                report.append(f"\n#### Open Access")
                report.append(f"- Status: {'✅ Open' if oa.get('is_oa') else '❌ Closed'}")
                report.append(f"- Type: {oa.get('oa_status', 'N/A')}")

            # Internal importance
            if 'internal_graph' in components:
                graph = components['internal_graph']
                report.append(f"\n#### Internal Corpus Importance")
                report.append(f"- PageRank: {graph.get('pagerank', 0):.4f}")
                report.append(f"- In-degree: {graph.get('in_degree', 0)} citations")
                report.append(f"- Authority Score: {graph.get('authority_score', 0):.4f}")

            # Recommendations
            if impact.get('recommendations'):
                report.append("\n## Recommendations\n")
                for rec in impact['recommendations']:
                    report.append(f"- {rec}")

        # Save if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report))
            logger.info(f"Impact report saved to: {output_path}")

        return '\n'.join(report)


def main():
    """Test enhanced document metadata agent."""
    print("Testing Enhanced Document Metadata Agent with Impact Assessment...")

    # Initialize
    agent = EnhancedDocumentMetadataAgent(
        output_dir=Path("results/enhanced_metadata"),
        email="test@example.com",
        enable_impact=True
    )

    # Create test metadata (simulate what we'd get from a real document)
    test_metadata = {
        'title': 'Deep Learning',
        'authors': ['Ian Goodfellow', 'Yoshua Bengio', 'Aaron Courville'],
        'year': 2016,
        'doi': '10.1038/nature14236',  # Using a real DOI for testing
        'document_type': 'book',
        'pdf_filename': 'deep_learning.pdf',
        'document_id': 'dl_2016'
    }

    print("\n=== Calculating Impact Assessment ===")
    impact_data = agent._calculate_impact(test_metadata)

    print("\n=== Impact Results ===")
    print(f"Composite Score: {impact_data['composite_score']:.2f}")
    print(f"Reliability Level: {impact_data['reliability_level']}")

    if impact_data.get('recommendations'):
        print("\n=== Recommendations ===")
        for rec in impact_data['recommendations']:
            print(f"- {rec}")

    # Generate report
    test_metadata['impact'] = impact_data
    print("\n=== Generating Report ===")
    report = agent.generate_impact_report(
        test_metadata,
        output_path=Path("results/impact_report.md")
    )

    print("\n✅ Enhanced Document Metadata Agent test complete")
    print("Report saved to: results/impact_report.md")


if __name__ == "__main__":
    main()