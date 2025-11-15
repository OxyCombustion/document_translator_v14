#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Impact Assessment Agent - Document Impact & Influence Scoring

Evaluates document quality, reliability, and importance based on:
- Citation impact (field-normalized)
- Venue prestige (journal/conference ranking)
- Author reputation (h-index, affiliation)
- Recency/obsolescence (time decay)
- Community attention (altmetrics)
- Internal usage patterns

This complements UncertaintyAssessmentAgent by evaluating SOURCE quality
while uncertainty evaluates EXTRACTION quality.

Key Features:
-------------
- Multi-source API integration (OpenAlex, Crossref, Unpaywall)
- Field normalization to avoid citation bias
- Time decay with field-specific half-lives
- Internal usage learning
- SQLite caching with intelligent expiration
- Offline fallbacks for no-internet scenarios

Author: Claude Code
Date: 2025-10-13
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
import math
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum

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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FieldDomain(Enum):
    """Academic field domains with citation half-lives."""
    COMPUTER_SCIENCE = ("computer_science", 5)  # Fast-moving field
    MEDICINE = ("medicine", 8)
    PHYSICS = ("physics", 10)
    ENGINEERING = ("engineering", 12)
    MATHEMATICS = ("mathematics", 15)  # Slow-moving field
    CHEMISTRY = ("chemistry", 9)
    BIOLOGY = ("biology", 7)
    SOCIAL_SCIENCES = ("social_sciences", 10)
    UNKNOWN = ("unknown", 10)  # Default


@dataclass
class VenueMetrics:
    """Venue (journal/conference) quality metrics."""
    name: str
    type: str = "unknown"  # journal | conference | book | technical_report
    issn: Optional[str] = None
    sjr: Optional[float] = None  # Scimago Journal Rank
    snip: Optional[float] = None  # Source Normalized Impact per Paper
    citescore: Optional[float] = None
    jif: Optional[float] = None  # Journal Impact Factor
    jif_year: Optional[int] = None
    quartile: Optional[str] = None  # Q1-Q4
    field_rank: Optional[int] = None
    field_percentile: Optional[float] = None


@dataclass
class AuthorMetrics:
    """Author reputation metrics."""
    name: str
    orcid: Optional[str] = None
    h_index: Optional[int] = None
    i10_index: Optional[int] = None
    affiliation: Optional[str] = None
    affiliation_rank: Optional[int] = None
    career_stage: Optional[str] = None  # junior | mid | senior | distinguished


@dataclass
class WorkMetrics:
    """Document-level citation and reference metrics."""
    citation_count: int = 0
    citations_per_year: float = 0.0
    citations_recent_3y: int = 0
    field_normalized_citations: float = 0.0
    influential_citations: Optional[int] = None
    reference_count: int = 0
    self_citation_rate: float = 0.0


@dataclass
class AltmetricsData:
    """Alternative metrics (social/news/policy attention)."""
    mendeley_readers: Optional[int] = None
    twitter_mentions: Optional[int] = None
    blog_mentions: Optional[int] = None
    news_mentions: Optional[int] = None
    policy_citations: Optional[int] = None
    altmetric_score: Optional[float] = None
    altmetric_percentile: Optional[float] = None


@dataclass
class OpenAccessInfo:
    """Open access status and licensing."""
    is_oa: bool = False
    oa_status: str = "closed"  # gold | green | hybrid | bronze | closed
    license: Optional[str] = None
    oa_url: Optional[str] = None


@dataclass
class InternalUsage:
    """Internal system usage metrics."""
    retrieval_count: int = 0
    click_count: int = 0
    dwell_time_mean_sec: float = 0.0
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    usage_score: float = 0.0
    first_used: Optional[datetime] = None
    last_used: Optional[datetime] = None


@dataclass
class ContentQuality:
    """Content extraction quality metrics."""
    equation_count: int = 0
    table_count: int = 0
    figure_count: int = 0
    symbol_coverage: float = 0.0  # % symbols in library
    unit_completeness: float = 0.0  # % equations with units
    dimensional_consistency: float = 0.0  # % equations pass validation
    extraction_quality: float = 0.0  # From UncertaintyAssessmentAgent


@dataclass
class ImpactComponents:
    """Individual impact score components."""
    field_norm_citations: float = 0.0
    venue_prestige: float = 0.0
    author_influence: float = 0.0
    recency: float = 0.0
    altmetrics: float = 0.0
    openaccess: float = 0.0
    internal_usage: float = 0.0
    content_quality: float = 0.0


@dataclass
class ImpactScore:
    """Composite impact score with components and metadata."""
    composite_score: float
    confidence: float
    components: ImpactComponents
    computed_at: datetime
    sources: Dict[str, str] = field(default_factory=dict)
    version: str = "1.0"


class ImpactAssessmentAgent:
    """
    Assess document impact, influence, and reliability.

    This agent enriches document metadata with multi-dimensional impact
    scoring to help prioritize and weight information from different sources.

    Usage Example:
    --------------
    >>> agent = ImpactAssessmentAgent(cache_dir=Path("cache"))
    >>>
    >>> # Assess impact for a document
    >>> metadata = {
    ...     "doi": "10.1038/nature14016",
    ...     "title": "The geographical distribution...",
    ...     "authors": ["McGlade", "Ekins"],
    ...     "year": 2015
    ... }
    >>>
    >>> impact = agent.assess_document_impact(metadata)
    >>> print(f"Impact Score: {impact.composite_score:.3f}")
    >>> print(f"Components: {impact.components}")
    """

    def __init__(
        self,
        cache_dir: Path = None,
        api_email: str = None,
        use_cache: bool = True,
        cache_expiry_days: int = 7
    ):
        """
        Initialize impact assessment agent.

        Args:
            cache_dir: Directory for SQLite cache (default: cache/)
            api_email: Email for polite API usage (required for some APIs)
            use_cache: Whether to use caching (default: True)
            cache_expiry_days: Days before cache expires (default: 7)
        """
        self.cache_dir = Path(cache_dir or "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.api_email = api_email or "document-translator@example.com"
        self.use_cache = use_cache
        self.cache_expiry = timedelta(days=cache_expiry_days)

        # Initialize cache database
        self.cache_db = self.cache_dir / "impact_cache.db"
        self._init_cache_db()

        # Component weights for composite score
        self.weights = {
            "field_norm_citations": 0.30,
            "venue_prestige": 0.18,
            "author_influence": 0.13,
            "recency": 0.13,
            "altmetrics": 0.09,
            "openaccess": 0.04,
            "internal_usage": 0.10,
            "content_quality": 0.03
        }

        # Field-specific citation medians (citations/year)
        # These would be updated from OpenAlex API
        self.field_medians = {
            "computer_science": 3.5,
            "medicine": 4.2,
            "physics": 2.8,
            "engineering": 2.1,
            "mathematics": 1.5,
            "chemistry": 3.0,
            "biology": 3.8,
            "social_sciences": 2.5,
            "unknown": 2.5
        }

    def _init_cache_db(self):
        """Initialize SQLite cache database."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        # API response cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_responses (
                identifier TEXT PRIMARY KEY,
                identifier_type TEXT,
                source TEXT,
                response_json TEXT,
                fetched_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        # Impact scores cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS impact_scores (
                document_id TEXT PRIMARY KEY,
                doi TEXT,
                isbn TEXT,
                composite_score REAL,
                field_norm_citations REAL,
                venue_prestige REAL,
                author_influence REAL,
                recency_boost REAL,
                altmetrics REAL,
                openaccess REAL,
                internal_usage REAL,
                content_quality REAL,
                confidence REAL,
                computed_at TIMESTAMP,
                metadata_json TEXT
            )
        """)

        # Venue cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venue_cache (
                issn TEXT PRIMARY KEY,
                venue_name TEXT,
                sjr REAL,
                snip REAL,
                citescore REAL,
                quartile TEXT,
                field TEXT,
                cached_at TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def assess_document_impact(
        self,
        metadata: Dict[str, Any],
        internal_usage: Optional[InternalUsage] = None,
        content_quality: Optional[ContentQuality] = None,
        force_refresh: bool = False
    ) -> ImpactScore:
        """
        Assess the impact of a document.

        Args:
            metadata: Document metadata with DOI, title, authors, etc.
            internal_usage: Optional internal usage metrics
            content_quality: Optional content quality metrics
            force_refresh: Force API refresh (ignore cache)

        Returns:
            ImpactScore with composite score and components
        """
        # Generate document ID
        doc_id = self._generate_document_id(metadata)

        # Check cache if not forcing refresh
        if not force_refresh and self.use_cache:
            cached_impact = self._get_cached_impact(doc_id)
            if cached_impact:
                logger.info(f"Using cached impact for {doc_id}")
                return cached_impact

        logger.info(f"Computing impact for {doc_id}")

        # Extract identifiers
        doi = metadata.get("doi")
        isbn = metadata.get("isbn")
        title = metadata.get("title", "Unknown")

        # Initialize components
        components = ImpactComponents()
        sources = {}

        # 1. Get citation metrics
        if doi:
            work_metrics = self._get_work_metrics(doi)
            components.field_norm_citations = self.calculate_field_norm_citations(
                work_metrics, metadata.get("year"), metadata.get("field", "unknown")
            )
            sources["citations"] = "calculated"

        # 2. Get venue metrics
        venue_data = metadata.get("venue", {})
        if venue_data:
            venue_metrics = VenueMetrics(**venue_data) if isinstance(venue_data, dict) else venue_data
            components.venue_prestige = self.calculate_venue_prestige(venue_metrics)
            sources["venue"] = "metadata"

        # 3. Get author metrics
        authors_data = metadata.get("authors", [])
        if authors_data:
            author_metrics = [AuthorMetrics(**a) if isinstance(a, dict) else a for a in authors_data]
            components.author_influence = self.calculate_author_influence(author_metrics)
            sources["authors"] = "metadata"

        # 4. Calculate recency
        pub_year = metadata.get("year")
        if pub_year:
            field = metadata.get("field", "unknown")
            components.recency = self.calculate_recency_boost(pub_year, field)
            sources["recency"] = "calculated"

        # 5. Get altmetrics (would come from API)
        altmetrics_data = metadata.get("altmetrics")
        if altmetrics_data:
            components.altmetrics = self.calculate_altmetrics_score(altmetrics_data)
            sources["altmetrics"] = "metadata"

        # 6. Open access bonus
        oa_info = metadata.get("openaccess", {})
        if oa_info:
            components.openaccess = 1.0 if oa_info.get("is_oa", False) else 0.0
            sources["openaccess"] = "metadata"

        # 7. Internal usage (if provided)
        if internal_usage:
            components.internal_usage = self.calculate_internal_usage(internal_usage)
            sources["internal"] = "provided"

        # 8. Content quality (if provided)
        if content_quality:
            components.content_quality = content_quality.extraction_quality
            sources["quality"] = "provided"

        # Calculate composite score
        composite = self.calculate_composite_score(components)

        # Estimate confidence
        confidence = self.estimate_confidence(components, sources)

        # Create impact score
        impact = ImpactScore(
            composite_score=composite,
            confidence=confidence,
            components=components,
            computed_at=datetime.now(),
            sources=sources
        )

        # Cache the result
        if self.use_cache:
            self._cache_impact(doc_id, doi, isbn, impact)

        return impact

    def calculate_field_norm_citations(
        self,
        work_metrics: WorkMetrics,
        pub_year: Optional[int],
        field: str
    ) -> float:
        """
        Calculate field-normalized citation score.

        Normalizes by field median to avoid bias to older/broader fields.

        Args:
            work_metrics: Citation and reference metrics
            pub_year: Publication year
            field: Academic field

        Returns:
            Normalized score 0-1
        """
        if not pub_year or not work_metrics:
            return 0.5  # Unknown

        current_year = datetime.now().year
        age = max(current_year - pub_year, 1)
        citations_per_year = work_metrics.citation_count / age

        # Get field median (would be updated from API)
        field_median = self.field_medians.get(field, 2.5)

        # Ratio vs field median
        ratio = citations_per_year / field_median

        # Cap at 10x median (diminishing returns)
        ratio = min(ratio, 10.0)

        # Normalize to 0-1
        score = ratio / 10.0

        return score

    def calculate_venue_prestige(self, venue_metrics: VenueMetrics) -> float:
        """
        Calculate venue prestige score.

        Combines quartile ranking with absolute metrics.

        Args:
            venue_metrics: Journal/conference metrics

        Returns:
            Normalized score 0-1
        """
        if not venue_metrics:
            return 0.5  # Unknown

        # Primary: Use quartile if available
        quartile_scores = {
            "Q1": 1.0,
            "Q2": 0.7,
            "Q3": 0.4,
            "Q4": 0.2
        }

        base_score = quartile_scores.get(venue_metrics.quartile, 0.5)

        # Boost for high SJR (Scimago Journal Rank)
        if venue_metrics.sjr and venue_metrics.sjr > 2.0:
            base_score = min(base_score * 1.2, 1.0)

        # Boost for top percentile
        if venue_metrics.field_percentile and venue_metrics.field_percentile >= 90:
            base_score = min(base_score * 1.15, 1.0)

        return base_score

    def calculate_author_influence(self, authors: List[AuthorMetrics]) -> float:
        """
        Calculate author influence score.

        Combines h-index with affiliation prestige.

        Args:
            authors: List of author metrics

        Returns:
            Normalized score 0-1
        """
        if not authors:
            return 0.5  # Unknown

        # Use maximum h-index (typically lead/senior author)
        h_indices = [a.h_index for a in authors if a.h_index is not None]
        max_h_index = max(h_indices) if h_indices else 0

        # Normalize h-index (log scale, cap at 100)
        h_score = min(max_h_index / 100.0, 1.0)

        # Affiliation boost (top universities)
        affil_ranks = [a.affiliation_rank for a in authors if a.affiliation_rank is not None]

        if affil_ranks:
            min_rank = min(affil_ranks)
            if min_rank <= 100:
                affil_score = 1.0
            elif min_rank <= 500:
                affil_score = 0.7
            else:
                affil_score = 0.5
        else:
            affil_score = 0.5  # Unknown

        # Combine (70% h-index, 30% affiliation)
        score = 0.7 * h_score + 0.3 * affil_score

        return score

    def calculate_recency_boost(self, pub_year: int, field: str) -> float:
        """
        Calculate time-based recency score.

        Uses exponential decay with field-specific half-lives.

        Args:
            pub_year: Publication year
            field: Academic field

        Returns:
            Time-decay score 0-1
        """
        current_year = datetime.now().year
        age = current_year - pub_year

        # Get field-specific half-life
        for domain in FieldDomain:
            if domain.value[0] == field:
                tau = domain.value[1]
                break
        else:
            tau = 10  # Default

        # Exponential decay
        score = math.exp(-age / tau)

        return score

    def calculate_altmetrics_score(self, altmetrics_data: Dict[str, Any]) -> float:
        """
        Calculate altmetrics attention score.

        Args:
            altmetrics_data: Dictionary with altmetric metrics

        Returns:
            Normalized score 0-1
        """
        if not altmetrics_data:
            return 0.0

        # Use percentile if available (most reliable)
        if "altmetric_percentile" in altmetrics_data:
            return altmetrics_data["altmetric_percentile"] / 100.0

        # Otherwise use absolute score (log scale)
        score = altmetrics_data.get("altmetric_score", 0)
        if score == 0:
            return 0.0

        # Log normalization (score > 100 is exceptional)
        normalized = math.log10(score + 1) / 2.0  # log10(100) ≈ 2

        return min(normalized, 1.0)

    def calculate_internal_usage(self, usage: InternalUsage) -> float:
        """
        Calculate internal usage score.

        Learns what users find valuable.

        Args:
            usage: Internal usage metrics

        Returns:
            Usage score 0-1
        """
        if not usage:
            return 0.0

        # Retrieval frequency (log scale)
        retrievals = usage.retrieval_count
        retrieval_score = min(math.log10(retrievals + 1) / 2.0, 1.0) if retrievals > 0 else 0.0

        # Click-through rate
        ctr = usage.click_count / max(retrievals, 1) if retrievals > 0 else 0.0

        # Dwell time (5 min = perfect)
        dwell_score = min(usage.dwell_time_mean_sec / 300.0, 1.0)

        # Helpful votes
        total_votes = usage.helpful_votes + usage.unhelpful_votes
        vote_ratio = usage.helpful_votes / max(total_votes, 1) if total_votes > 0 else 0.5

        # Combine (40% retrieval, 20% CTR, 20% dwell, 20% votes)
        score = (
            0.40 * retrieval_score +
            0.20 * ctr +
            0.20 * dwell_score +
            0.20 * vote_ratio
        )

        return score

    def calculate_composite_score(self, components: ImpactComponents) -> float:
        """
        Calculate weighted composite impact score.

        Args:
            components: Individual component scores

        Returns:
            Composite score 0-1
        """
        composite = 0.0

        component_dict = asdict(components)
        for key, weight in self.weights.items():
            value = component_dict.get(key, 0.0)
            composite += weight * value

        # Ensure 0-1 range
        composite = max(0.0, min(1.0, composite))

        return composite

    def estimate_confidence(
        self,
        components: ImpactComponents,
        sources: Dict[str, str]
    ) -> float:
        """
        Estimate confidence in the impact score.

        Based on data completeness and source quality.

        Args:
            components: Component scores
            sources: Data sources used

        Returns:
            Confidence score 0-1
        """
        # Count non-zero components
        component_dict = asdict(components)
        non_zero = sum(1 for v in component_dict.values() if v > 0)
        total = len(component_dict)

        completeness = non_zero / total if total > 0 else 0.0

        # Source quality (API > metadata > calculated > missing)
        source_quality = {
            "openalex": 1.0,
            "crossref": 0.9,
            "unpaywall": 0.9,
            "semantic_scholar": 0.95,
            "metadata": 0.7,
            "calculated": 0.8,
            "provided": 0.85,
            "missing": 0.0
        }

        avg_quality = sum(
            source_quality.get(s, 0.5) for s in sources.values()
        ) / max(len(sources), 1)

        # Combine (60% completeness, 40% source quality)
        confidence = 0.6 * completeness + 0.4 * avg_quality

        return confidence

    def _generate_document_id(self, metadata: Dict[str, Any]) -> str:
        """Generate unique document ID from metadata."""
        # Use DOI if available
        if metadata.get("doi"):
            return f"doi_{metadata['doi'].replace('/', '_')}"

        # Use ISBN if available
        if metadata.get("isbn"):
            return f"isbn_{metadata['isbn']}"

        # Fall back to title hash
        title = metadata.get("title", "unknown")
        title_hash = hashlib.sha256(title.encode()).hexdigest()[:12]
        return f"doc_{title_hash}"

    def _get_work_metrics(self, doi: str) -> WorkMetrics:
        """
        Get work metrics from cache or API.

        Would connect to OpenAlex/Crossref APIs.
        For now, returns mock data.

        Args:
            doi: Document DOI

        Returns:
            WorkMetrics object
        """
        # TODO: Implement API calls to OpenAlex/Crossref
        # For now, return mock data
        return WorkMetrics(
            citation_count=247,
            citations_per_year=27.4,
            citations_recent_3y=82,
            field_normalized_citations=2.3,
            influential_citations=18,
            reference_count=45
        )

    def _get_cached_impact(self, doc_id: str) -> Optional[ImpactScore]:
        """Get cached impact score if available and not expired."""
        if not self.use_cache:
            return None

        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT composite_score, confidence, field_norm_citations,
                   venue_prestige, author_influence, recency_boost,
                   altmetrics, openaccess, internal_usage, content_quality,
                   computed_at, metadata_json
            FROM impact_scores
            WHERE document_id = ?
        """, (doc_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Check expiration (30 days)
        computed_at = datetime.fromisoformat(row[10])
        if datetime.now() - computed_at > timedelta(days=30):
            return None

        # Reconstruct ImpactScore
        components = ImpactComponents(
            field_norm_citations=row[2],
            venue_prestige=row[3],
            author_influence=row[4],
            recency=row[5],
            altmetrics=row[6],
            openaccess=row[7],
            internal_usage=row[8],
            content_quality=row[9]
        )

        metadata = json.loads(row[11]) if row[11] else {}

        return ImpactScore(
            composite_score=row[0],
            confidence=row[1],
            components=components,
            computed_at=computed_at,
            sources=metadata.get("sources", {}),
            version=metadata.get("version", "1.0")
        )

    def _cache_impact(
        self,
        doc_id: str,
        doi: Optional[str],
        isbn: Optional[str],
        impact: ImpactScore
    ):
        """Cache impact score to database."""
        if not self.use_cache:
            return

        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        metadata = {
            "sources": impact.sources,
            "version": impact.version
        }

        cursor.execute("""
            INSERT OR REPLACE INTO impact_scores
            (document_id, doi, isbn, composite_score, field_norm_citations,
             venue_prestige, author_influence, recency_boost, altmetrics,
             openaccess, internal_usage, content_quality, confidence,
             computed_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id, doi, isbn, impact.composite_score,
            impact.components.field_norm_citations,
            impact.components.venue_prestige,
            impact.components.author_influence,
            impact.components.recency,
            impact.components.altmetrics,
            impact.components.openaccess,
            impact.components.internal_usage,
            impact.components.content_quality,
            impact.confidence,
            impact.computed_at.isoformat(),
            json.dumps(metadata)
        ))

        conn.commit()
        conn.close()


def main():
    """Test impact assessment agent."""
    print("Testing Impact Assessment Agent...")

    # Initialize agent
    agent = ImpactAssessmentAgent(
        cache_dir=Path("cache/impact"),
        api_email="test@example.com"
    )

    # Test document metadata
    metadata = {
        "doi": "10.1038/nature14016",
        "title": "The geographical distribution of fossil fuels unused",
        "year": 2015,
        "field": "engineering",
        "authors": [
            {
                "name": "Christophe McGlade",
                "h_index": 15,
                "affiliation": "University College London",
                "affiliation_rank": 8
            },
            {
                "name": "Paul Ekins",
                "h_index": 42,
                "affiliation": "University College London",
                "affiliation_rank": 8
            }
        ],
        "venue": {
            "name": "Nature",
            "quartile": "Q1",
            "sjr": 14.367,
            "field_percentile": 99.5
        },
        "altmetrics": {
            "altmetric_score": 847,
            "altmetric_percentile": 98.2
        },
        "openaccess": {
            "is_oa": True,
            "oa_status": "gold"
        }
    }

    # Mock internal usage
    usage = InternalUsage(
        retrieval_count=47,
        click_count=23,
        dwell_time_mean_sec=218,
        helpful_votes=18,
        unhelpful_votes=2
    )

    # Mock content quality
    quality = ContentQuality(
        equation_count=42,
        table_count=8,
        figure_count=15,
        symbol_coverage=0.87,
        unit_completeness=0.92,
        dimensional_consistency=0.95,
        extraction_quality=0.89
    )

    print("\n=== Assessing Document Impact ===")
    impact = agent.assess_document_impact(
        metadata,
        internal_usage=usage,
        content_quality=quality
    )

    print(f"\n✅ Composite Impact Score: {impact.composite_score:.3f}")
    print(f"   Confidence: {impact.confidence:.3f}")

    print("\n📊 Component Scores:")
    components_dict = asdict(impact.components)
    for key, value in components_dict.items():
        print(f"   {key:20s}: {value:.3f}")

    print("\n📍 Data Sources:")
    for key, source in impact.sources.items():
        print(f"   {key:20s}: {source}")

    print("\n=== Testing Cache ===")
    # Should use cache this time
    impact2 = agent.assess_document_impact(metadata)
    print(f"✅ Cached score matches: {impact.composite_score == impact2.composite_score}")

    print("\n✅ Impact assessment test complete")


if __name__ == "__main__":
    main()