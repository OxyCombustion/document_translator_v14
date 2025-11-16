#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crossref API Client - Bibliographic Metadata

Crossref is a DOI registration agency that provides free access to
metadata for 130+ million scholarly works.

API Documentation: https://github.com/CrossRef/rest-api-doc

Key Features:
- Free access, no API key required
- Polite pool with email (50 req/sec)
- Reference lists for citation tracking
- Funder information
- License metadata

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


class CrossrefClient:
    """
    Client for Crossref REST API.

    Provides access to DOI metadata, references, and bibliographic information.
    Uses polite pool for higher rate limits (50 req/sec with email).

    Example:
        >>> client = CrossrefClient(email="your@email.com")
        >>> work = client.get_work("10.1038/nature14016")
        >>> print(f"Title: {work['title'][0]}")
    """

    BASE_URL = "https://api.crossref.org"
    POLITE_RATE_LIMIT = 50  # requests per second with email
    DEFAULT_RATE_LIMIT = 10  # requests per second without email

    def __init__(
        self,
        email: str = None,
        cache_dir: Path = None,
        use_cache: bool = True,
        cache_expiry_days: int = 7
    ):
        """
        Initialize Crossref client.

        Args:
            email: Email for polite pool (50 req/sec)
            cache_dir: Directory for response cache
            use_cache: Whether to cache responses
            cache_expiry_days: Days before cache expires
        """
        self.email = email
        self.cache_dir = Path(cache_dir or "cache/crossref")
        self.use_cache = use_cache
        self.cache_expiry = timedelta(days=cache_expiry_days)

        # Create cache directory
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Set up session
        self.session = requests.Session()
        if email:
            self.session.headers.update({
                "User-Agent": f"document-translator/1.0 (mailto:{email})"
            })
            self.rate_limit = self.POLITE_RATE_LIMIT
        else:
            self.session.headers.update({
                "User-Agent": "document-translator/1.0"
            })
            self.rate_limit = self.DEFAULT_RATE_LIMIT

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.rate_limit

    def get_work(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get work metadata by DOI.

        Args:
            doi: Document DOI (e.g., "10.1038/nature14016")

        Returns:
            Work metadata including title, authors, journal, references
        """
        # Check cache
        cache_key = f"work_{doi.replace('/', '_')}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build URL
        url = f"{self.BASE_URL}/works/{doi}"

        # Make request
        response = self._make_request(url)
        if not response:
            return None

        work = response.get("message")
        if work:
            self._save_cache(cache_key, work)

        return work

    def search_works(
        self,
        query: str = None,
        title: str = None,
        author: str = None,
        year: int = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for works.

        Args:
            query: General search query
            title: Title to search for
            author: Author name
            year: Publication year
            limit: Maximum results

        Returns:
            List of matching works
        """
        # Build query parameters
        params = {
            "rows": limit
        }

        # Add search criteria
        if query:
            params["query"] = query
        if title:
            params["query.title"] = title
        if author:
            params["query.author"] = author

        # Add filters
        filters = []
        if year:
            filters.append(f"from-pub-date:{year},until-pub-date:{year}")

        if filters:
            params["filter"] = ",".join(filters)

        # Make request
        url = f"{self.BASE_URL}/works"
        response = self._make_request(url, params=params)

        if not response:
            return []

        return response.get("message", {}).get("items", [])

    def get_journal(self, issn: str) -> Optional[Dict[str, Any]]:
        """
        Get journal metadata by ISSN.

        Args:
            issn: Journal ISSN (e.g., "1476-4687")

        Returns:
            Journal metadata
        """
        # Check cache
        cache_key = f"journal_{issn.replace('-', '_')}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build URL
        url = f"{self.BASE_URL}/journals/{issn}"

        # Make request
        response = self._make_request(url)
        if not response:
            return None

        journal = response.get("message")
        if journal:
            self._save_cache(cache_key, journal)

        return journal

    def get_member(self, member_id: str) -> Optional[Dict[str, Any]]:
        """
        Get publisher/member metadata.

        Args:
            member_id: Crossref member ID

        Returns:
            Publisher metadata
        """
        # Check cache
        cache_key = f"member_{member_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build URL
        url = f"{self.BASE_URL}/members/{member_id}"

        # Make request
        response = self._make_request(url)
        if not response:
            return None

        member = response.get("message")
        if member:
            self._save_cache(cache_key, member)

        return member

    def get_references(self, doi: str) -> List[Dict[str, Any]]:
        """
        Get references for a work.

        Args:
            doi: Document DOI

        Returns:
            List of references
        """
        work = self.get_work(doi)
        if not work:
            return []

        return work.get("reference", [])

    def extract_impact_metrics(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract impact-relevant metrics from Crossref work.

        Args:
            work: Work metadata from get_work()

        Returns:
            Structured impact metrics
        """
        metrics = {
            "doi": work.get("DOI"),
            "title": work.get("title", [""])[0] if work.get("title") else None,
            "type": work.get("type"),
            "url": work.get("URL")
        }

        # Publication date
        date_parts = work.get("published-print", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            metrics["publication_year"] = date_parts[0][0] if len(date_parts[0]) > 0 else None
            metrics["publication_month"] = date_parts[0][1] if len(date_parts[0]) > 1 else None
            metrics["publication_day"] = date_parts[0][2] if len(date_parts[0]) > 2 else None

        # Authors
        authors = []
        for author_data in work.get("author", []):
            author = {
                "given": author_data.get("given"),
                "family": author_data.get("family"),
                "name": f"{author_data.get('given', '')} {author_data.get('family', '')}".strip(),
                "orcid": author_data.get("ORCID"),
                "affiliation": []
            }

            # Affiliations
            for affil in author_data.get("affiliation", []):
                author["affiliation"].append(affil.get("name"))

            authors.append(author)

        metrics["authors"] = authors
        metrics["author_count"] = len(authors)

        # Journal/Venue
        container = work.get("container-title", [""])[0] if work.get("container-title") else None
        if container:
            metrics["venue"] = {
                "name": container,
                "issn": work.get("ISSN", [""])[0] if work.get("ISSN") else None,
                "volume": work.get("volume"),
                "issue": work.get("issue"),
                "pages": work.get("page")
            }

        # Publisher
        metrics["publisher"] = {
            "name": work.get("publisher"),
            "member_id": work.get("member")
        }

        # References and citations
        metrics["references"] = {
            "count": work.get("reference-count", 0),
            "list": len(work.get("reference", []))
        }

        # Note: Crossref has limited citation data compared to OpenAlex
        metrics["citations"] = {
            "is_referenced_by_count": work.get("is-referenced-by-count", 0)
        }

        # Funding information
        funders = []
        for funder in work.get("funder", []):
            funders.append({
                "name": funder.get("name"),
                "doi": funder.get("DOI"),
                "award": funder.get("award", [])
            })
        metrics["funders"] = funders

        # License information
        licenses = []
        for license_data in work.get("license", []):
            licenses.append({
                "url": license_data.get("URL"),
                "start": license_data.get("start", {}).get("date-time"),
                "delay_days": license_data.get("delay-in-days", 0),
                "content_version": license_data.get("content-version")
            })
        metrics["licenses"] = licenses

        # Subject/categories
        subjects = work.get("subject", [])
        metrics["subjects"] = subjects

        # Links
        links = []
        for link in work.get("link", []):
            links.append({
                "url": link.get("URL"),
                "content_type": link.get("content-type"),
                "content_version": link.get("content-version"),
                "intended_application": link.get("intended-application")
            })
        metrics["links"] = links

        # Abstract (if available)
        abstract = work.get("abstract")
        if abstract:
            # Remove XML/HTML tags
            import re
            clean_abstract = re.sub('<[^<]+?>', '', abstract)
            metrics["abstract"] = clean_abstract

        # Clinical trial numbers (for medical papers)
        clinical_trials = work.get("clinical-trial-number", [])
        if clinical_trials:
            metrics["clinical_trials"] = clinical_trials

        return metrics

    def check_oa_status(self, work: Dict[str, Any]) -> Dict[str, str]:
        """
        Check open access status from license information.

        Args:
            work: Work metadata

        Returns:
            OA status information
        """
        licenses = work.get("license", [])

        oa_info = {
            "is_oa": False,
            "oa_type": "closed",
            "license": None
        }

        # Check for open licenses
        open_licenses = [
            "creativecommons.org",
            "opensource.org",
            "publicdomain"
        ]

        for license_data in licenses:
            url = license_data.get("URL", "").lower()
            for open_lic in open_licenses:
                if open_lic in url:
                    oa_info["is_oa"] = True
                    oa_info["oa_type"] = "open"
                    oa_info["license"] = url
                    break

        return oa_info

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make rate-limited request to Crossref API.

        Args:
            url: API URL
            params: Query parameters

        Returns:
            JSON response or None
        """
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        try:
            logger.debug(f"Requesting: {url}")
            response = self.session.get(url, params=params, timeout=30)
            self.last_request_time = time.time()

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Crossref API error: {e}")
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
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
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
        except Exception as e:
            logger.error(f"Cache write error: {e}")


def main():
    """Test Crossref client."""
    print("Testing Crossref Client...")

    # Initialize client
    client = CrossrefClient(
        email="test@example.com",
        cache_dir=Path("cache/crossref")
    )

    # Test DOI lookup
    doi = "10.1038/nature14016"
    print(f"\n=== Getting work: {doi} ===")
    work = client.get_work(doi)

    if work:
        print(f"✅ Found: {work.get('title', [''])[0][:80]}...")
        print(f"   Type: {work.get('type')}")
        print(f"   Publisher: {work.get('publisher')}")

        # Extract metrics
        print("\n=== Extracting Metrics ===")
        metrics = client.extract_impact_metrics(work)

        print(f"   Year: {metrics.get('publication_year')}")
        print(f"   Authors: {metrics.get('author_count')}")
        if metrics['authors']:
            print(f"   First Author: {metrics['authors'][0]['name']}")

        if metrics.get("venue"):
            print(f"   Journal: {metrics['venue']['name']}")
            print(f"   Volume: {metrics['venue']['volume']}")
            print(f"   Pages: {metrics['venue']['pages']}")

        print(f"   References: {metrics['references']['count']}")
        print(f"   Citations: {metrics['citations'].get('is_referenced_by_count', 'N/A')}")

        if metrics.get("funders"):
            print(f"   Funders: {len(metrics['funders'])}")
            for funder in metrics['funders'][:2]:
                print(f"      - {funder['name']}")

        # Check OA status
        print("\n=== Open Access Status ===")
        oa_info = client.check_oa_status(work)
        print(f"   Is OA: {oa_info['is_oa']}")
        if oa_info['is_oa']:
            print(f"   License: {oa_info['license']}")

    else:
        print("❌ Work not found")

    # Test search
    print("\n=== Searching for works ===")
    results = client.search_works(title="machine learning", year=2024, limit=3)
    print(f"   Found {len(results)} results:")
    for work in results:
        title = work.get("title", [""])[0]
        print(f"      - {title[:60]}...")

    print("\n✅ Crossref client test complete")


if __name__ == "__main__":
    main()