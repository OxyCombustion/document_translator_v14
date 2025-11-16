#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenAlex API Client - Citation and Bibliographic Data

OpenAlex is a free, open catalog of over 250 million scholarly works.
This client provides polite, cached access to OpenAlex API.

API Documentation: https://docs.openalex.org

Key Features:
- Polite pool usage with email in User-Agent
- Automatic rate limiting (10 req/sec)
- Response caching with expiration
- Field-normalized citation metrics
- Author h-index and affiliations
- Venue quality metrics

Author: Claude Code
Date: 2025-10-13
Version: 1.0
"""

import sys
import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import requests
from urllib.parse import quote

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


class OpenAlexClient:
    """
    Client for OpenAlex API.

    Provides access to scholarly work metadata, citations, authors, and venues.
    Uses polite pool for faster rate limits (10 req/sec vs 1 req/sec).

    Example:
        >>> client = OpenAlexClient(email="your@email.com")
        >>> work = client.get_work_by_doi("10.1038/nature14016")
        >>> print(f"Citations: {work['cited_by_count']}")
    """

    BASE_URL = "https://api.openalex.org"
    POLITE_RATE_LIMIT = 10  # requests per second with email
    DEFAULT_RATE_LIMIT = 1  # requests per second without email

    def __init__(
        self,
        email: str = None,
        cache_dir: Path = None,
        use_cache: bool = True,
        cache_expiry_days: int = 7
    ):
        """
        Initialize OpenAlex client.

        Args:
            email: Email for polite pool (10 req/sec). Required for best performance.
            cache_dir: Directory for response cache
            use_cache: Whether to cache responses
            cache_expiry_days: Days before cache expires
        """
        self.email = email
        self.cache_dir = Path(cache_dir or "cache/openalex")
        self.use_cache = use_cache
        self.cache_expiry = timedelta(days=cache_expiry_days)

        # Create cache directory
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Set up session with User-Agent
        self.session = requests.Session()
        if email:
            self.session.headers.update({
                "User-Agent": f"mailto:{email}; document-translator/1.0"
            })
            self.rate_limit = self.POLITE_RATE_LIMIT
        else:
            self.session.headers.update({
                "User-Agent": "document-translator/1.0"
            })
            self.rate_limit = self.DEFAULT_RATE_LIMIT
            logger.warning("No email provided - using slower rate limit (1 req/sec). "
                         "Provide email for 10x faster access.")

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.rate_limit

    def get_work_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get work metadata by DOI.

        Args:
            doi: Document DOI (e.g., "10.1038/nature14016")

        Returns:
            Work metadata including citations, venue, authors, concepts
        """
        # Check cache first
        cache_key = f"work_doi_{doi.replace('/', '_')}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build URL (DOI needs special handling)
        url = f"{self.BASE_URL}/works/https://doi.org/{doi}"

        # Make request
        response = self._make_request(url)
        if not response:
            return None

        # Cache and return
        self._save_cache(cache_key, response)
        return response

    def get_work(self, openalex_id: str) -> Optional[Dict[str, Any]]:
        """
        Get work by OpenAlex ID.

        Args:
            openalex_id: OpenAlex work ID (e.g., "W2104348020")

        Returns:
            Work metadata
        """
        # Check cache
        cache_key = f"work_{openalex_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Make request
        url = f"{self.BASE_URL}/works/{openalex_id}"
        response = self._make_request(url)

        if response:
            self._save_cache(cache_key, response)

        return response

    def search_works(
        self,
        title: str = None,
        author: str = None,
        year: int = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for works.

        Args:
            title: Title to search for
            author: Author name
            year: Publication year
            limit: Maximum results to return

        Returns:
            List of matching works
        """
        # Build search query
        filters = []
        if title:
            filters.append(f"title.search:{quote(title)}")
        if author:
            filters.append(f"author.search:{quote(author)}")
        if year:
            filters.append(f"publication_year:{year}")

        if not filters:
            logger.error("No search criteria provided")
            return []

        # Build URL
        filter_str = ",".join(filters)
        url = f"{self.BASE_URL}/works?filter={filter_str}&per-page={limit}"

        # Make request
        response = self._make_request(url)
        if not response:
            return []

        return response.get("results", [])

    def get_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        """
        Get author metadata.

        Args:
            author_id: OpenAlex author ID or ORCID

        Returns:
            Author metadata including h-index, works count, affiliation
        """
        # Check cache
        cache_key = f"author_{author_id.replace('/', '_')}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Handle ORCID
        if author_id.startswith("0000-"):
            url = f"{self.BASE_URL}/authors/https://orcid.org/{author_id}"
        else:
            url = f"{self.BASE_URL}/authors/{author_id}"

        # Make request
        response = self._make_request(url)

        if response:
            self._save_cache(cache_key, response)

        return response

    def get_venue(self, venue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get venue (journal/conference) metadata.

        Args:
            venue_id: OpenAlex venue ID or ISSN

        Returns:
            Venue metadata including impact metrics
        """
        # Check cache
        cache_key = f"venue_{venue_id.replace('-', '_')}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Handle ISSN
        if len(venue_id) == 9 and venue_id[4] == '-':
            url = f"{self.BASE_URL}/venues/issn:{venue_id}"
        else:
            url = f"{self.BASE_URL}/venues/{venue_id}"

        # Make request
        response = self._make_request(url)

        if response:
            self._save_cache(cache_key, response)

        return response

    def get_concepts_for_work(self, work: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract concepts (fields/topics) from work.

        Args:
            work: Work metadata from get_work()

        Returns:
            List of concepts with scores
        """
        concepts = work.get("concepts", [])
        # Sort by score (relevance)
        concepts.sort(key=lambda x: x.get("score", 0), reverse=True)
        return concepts

    def get_field_normalized_citations(
        self,
        work: Dict[str, Any],
        field_medians: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate field-normalized citation score.

        Args:
            work: Work metadata
            field_medians: Optional field-specific medians (citations/year)

        Returns:
            Field-normalized score
        """
        # Get citations and age
        citations = work.get("cited_by_count", 0)
        pub_year = work.get("publication_year")

        if not pub_year:
            return 0.0

        age = datetime.now().year - pub_year
        if age <= 0:
            age = 1

        citations_per_year = citations / age

        # Get primary concept (field)
        concepts = self.get_concepts_for_work(work)
        primary_field = concepts[0]["display_name"].lower() if concepts else "unknown"

        # Default field medians if not provided
        if not field_medians:
            field_medians = {
                "computer science": 3.5,
                "medicine": 4.2,
                "physics": 2.8,
                "engineering": 2.1,
                "mathematics": 1.5,
                "chemistry": 3.0,
                "biology": 3.8,
                "social sciences": 2.5
            }

        # Find matching field
        field_median = 2.5  # default
        for field, median in field_medians.items():
            if field in primary_field:
                field_median = median
                break

        # Calculate normalized score
        if field_median > 0:
            return citations_per_year / field_median
        else:
            return citations_per_year / 2.5

    def extract_impact_metrics(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all impact-relevant metrics from work.

        Args:
            work: Work metadata from get_work()

        Returns:
            Dictionary with structured impact metrics
        """
        # Basic metadata
        metrics = {
            "openalex_id": work.get("id", "").split("/")[-1],
            "doi": work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
            "title": work.get("title"),
            "publication_year": work.get("publication_year"),
            "type": work.get("type")
        }

        # Citation metrics
        metrics["citations"] = {
            "total": work.get("cited_by_count", 0),
            "recent_works": work.get("cited_by_count_by_year", {}),
            "references": work.get("referenced_works_count", 0)
        }

        # Calculate recent citations (last 3 years)
        recent_citations = 0
        current_year = datetime.now().year
        for year_data in work.get("counts_by_year", []):
            year = year_data.get("year", 0)
            if current_year - year <= 3:
                recent_citations += year_data.get("cited_by_count", 0)
        metrics["citations"]["recent_3y"] = recent_citations

        # Venue information
        venue = work.get("primary_location", {}).get("source")
        if venue:
            metrics["venue"] = {
                "id": venue.get("id", "").split("/")[-1],
                "name": venue.get("display_name"),
                "type": venue.get("type"),
                "issn": venue.get("issn_l"),
                "is_oa": venue.get("is_oa", False),
                "host_organization": venue.get("host_organization_name")
            }

        # Author information
        authors = []
        for authorship in work.get("authorships", []):
            author_data = authorship.get("author", {})
            author = {
                "id": author_data.get("id", "").split("/")[-1],
                "name": author_data.get("display_name"),
                "orcid": author_data.get("orcid", "").replace("https://orcid.org/", "")
                        if author_data.get("orcid") else None
            }

            # Institution
            institutions = authorship.get("institutions", [])
            if institutions:
                inst = institutions[0]
                author["affiliation"] = inst.get("display_name")
                author["affiliation_country"] = inst.get("country_code")

            authors.append(author)

        metrics["authors"] = authors

        # Open Access status
        oa = work.get("open_access", {})
        metrics["open_access"] = {
            "is_oa": oa.get("is_oa", False),
            "oa_status": oa.get("oa_status"),
            "oa_url": oa.get("oa_url")
        }

        # Concepts (fields)
        concepts = self.get_concepts_for_work(work)
        metrics["fields"] = [
            {
                "name": c.get("display_name"),
                "score": c.get("score", 0)
            }
            for c in concepts[:5]  # Top 5 concepts
        ]

        # Sustainability Development Goals
        sdgs = work.get("sustainable_development_goals", [])
        if sdgs:
            metrics["sdgs"] = [
                {
                    "id": sdg.get("id"),
                    "name": sdg.get("display_name"),
                    "score": sdg.get("score", 0)
                }
                for sdg in sdgs
            ]

        return metrics

    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Make rate-limited request to OpenAlex API.

        Args:
            url: Full URL to request

        Returns:
            JSON response or None if error
        """
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        try:
            logger.debug(f"Requesting: {url}")
            response = self.session.get(url, timeout=30)
            self.last_request_time = time.time()

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAlex API error: {e}")
            return None

    def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        if not self.use_cache:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        # Check expiration
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime > self.cache_expiry:
            logger.debug(f"Cache expired for {cache_key}")
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                logger.debug(f"Using cached {cache_key}")
                return json.load(f)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def _save_cache(self, cache_key: str, data: Dict[str, Any]):
        """Save response to cache."""
        if not self.use_cache:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Cached {cache_key}")
        except Exception as e:
            logger.error(f"Cache write error: {e}")


def main():
    """Test OpenAlex client."""
    print("Testing OpenAlex Client...")

    # Initialize client
    client = OpenAlexClient(
        email="test@example.com",
        cache_dir=Path("cache/openalex")
    )

    # Test DOI lookup
    doi = "10.1038/nature14016"
    print(f"\n=== Getting work by DOI: {doi} ===")
    work = client.get_work_by_doi(doi)

    if work:
        print(f"✅ Found: {work.get('title')}")
        print(f"   Citations: {work.get('cited_by_count')}")
        print(f"   Year: {work.get('publication_year')}")

        # Extract impact metrics
        print("\n=== Extracting Impact Metrics ===")
        metrics = client.extract_impact_metrics(work)

        print(f"   OpenAlex ID: {metrics['openalex_id']}")
        print(f"   Citations (total): {metrics['citations']['total']}")
        print(f"   Citations (recent 3y): {metrics['citations']['recent_3y']}")
        print(f"   References: {metrics['citations']['references']}")

        if metrics.get("venue"):
            print(f"\n   Venue: {metrics['venue']['name']}")
            print(f"   Type: {metrics['venue']['type']}")
            print(f"   ISSN: {metrics['venue']['issn']}")

        print(f"\n   Authors ({len(metrics['authors'])}):")
        for author in metrics['authors'][:3]:  # First 3 authors
            print(f"      - {author['name']} ({author.get('affiliation', 'Unknown')})")

        print(f"\n   Open Access: {metrics['open_access']['is_oa']}")
        if metrics['open_access']['is_oa']:
            print(f"   OA Status: {metrics['open_access']['oa_status']}")

        print(f"\n   Fields:")
        for field in metrics.get("fields", [])[:3]:
            print(f"      - {field['name']} (score: {field['score']:.2f})")

        # Calculate field-normalized citations
        print("\n=== Field-Normalized Citations ===")
        fnc = client.get_field_normalized_citations(work)
        print(f"   Field-normalized score: {fnc:.2f}")

    else:
        print("❌ Work not found")

    # Test search
    print("\n=== Searching for works ===")
    results = client.search_works(title="climate change", year=2023, limit=3)
    print(f"   Found {len(results)} results:")
    for work in results:
        print(f"      - {work.get('title')[:60]}...")
        print(f"        Citations: {work.get('cited_by_count')}")

    print("\n✅ OpenAlex client test complete")


if __name__ == "__main__":
    main()