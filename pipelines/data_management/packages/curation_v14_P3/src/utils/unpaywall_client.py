#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unpaywall API Client - Open Access Status

Unpaywall provides free access to OA status for 30+ million scholarly articles.
Essential for determining if a document is freely accessible.

API Documentation: https://unpaywall.org/products/api

Key Features:
- Free access (100K requests/day)
- OA status (gold, green, hybrid, bronze, closed)
- Direct links to free PDFs
- License information
- Repository locations

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
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests

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


class UnpaywallClient:
    """
    Client for Unpaywall API.

    Provides open access status and free PDF locations for scholarly articles.
    Requires email for API access (free, no key needed).

    Example:
        >>> client = UnpaywallClient(email="your@email.com")
        >>> oa_info = client.get_oa_status("10.1038/nature14016")
        >>> if oa_info['is_oa']:
        >>>     print(f"Free PDF: {oa_info['best_oa_location']['url']}")
    """

    BASE_URL = "https://api.unpaywall.org/v2"
    RATE_LIMIT = 100000  # requests per day
    REQUESTS_PER_SECOND = 10  # Conservative rate limit

    def __init__(
        self,
        email: str,
        cache_dir: Path = None,
        use_cache: bool = True,
        cache_expiry_days: int = 30  # OA status changes slowly
    ):
        """
        Initialize Unpaywall client.

        Args:
            email: Email address (required by API)
            cache_dir: Directory for response cache
            use_cache: Whether to cache responses
            cache_expiry_days: Days before cache expires (default: 30)
        """
        if not email:
            raise ValueError("Email is required for Unpaywall API")

        self.email = email
        self.cache_dir = Path(cache_dir or "cache/unpaywall")
        self.use_cache = use_cache
        self.cache_expiry = timedelta(days=cache_expiry_days)

        # Create cache directory
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Set up session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"document-translator/1.0 ({email})"
        })

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.REQUESTS_PER_SECOND

    def get_oa_status(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get open access status for a DOI.

        Args:
            doi: Document DOI (e.g., "10.1038/nature14016")

        Returns:
            OA status including locations, license, and metadata
        """
        # Check cache
        cache_key = f"oa_{doi.replace('/', '_')}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build URL
        url = f"{self.BASE_URL}/{doi}"
        params = {"email": self.email}

        # Make request
        response = self._make_request(url, params=params)
        if response:
            self._save_cache(cache_key, response)

        return response

    def get_oa_locations(self, doi: str) -> List[Dict[str, Any]]:
        """
        Get all OA locations for a work.

        Args:
            doi: Document DOI

        Returns:
            List of OA locations with URLs and metadata
        """
        oa_info = self.get_oa_status(doi)
        if not oa_info:
            return []

        return oa_info.get("oa_locations", [])

    def get_best_oa_location(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get the best OA location for a work.

        Unpaywall ranks locations by quality (publisher > repository).

        Args:
            doi: Document DOI

        Returns:
            Best OA location or None if not OA
        """
        oa_info = self.get_oa_status(doi)
        if not oa_info or not oa_info.get("is_oa"):
            return None

        return oa_info.get("best_oa_location")

    def extract_oa_metrics(self, oa_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured OA metrics from Unpaywall data.

        Args:
            oa_data: Response from get_oa_status()

        Returns:
            Structured OA metrics
        """
        if not oa_data:
            return {
                "is_oa": False,
                "oa_status": "closed"
            }

        metrics = {
            "doi": oa_data.get("doi"),
            "is_oa": oa_data.get("is_oa", False),
            "oa_status": oa_data.get("oa_status", "closed"),
            "journal_is_oa": oa_data.get("journal_is_oa", False),
            "journal_is_in_doaj": oa_data.get("journal_is_in_doaj", False),
            "has_repository_copy": oa_data.get("has_repository_copy", False)
        }

        # Best OA location
        best_location = oa_data.get("best_oa_location")
        if best_location:
            metrics["best_oa_location"] = {
                "url": best_location.get("url"),
                "pmh_id": best_location.get("pmh_id"),
                "is_best": best_location.get("is_best"),
                "license": best_location.get("license"),
                "updated": best_location.get("updated"),
                "version": best_location.get("version"),
                "evidence": best_location.get("evidence"),
                "host_type": best_location.get("host_type"),  # publisher or repository
                "url_for_pdf": best_location.get("url_for_pdf"),
                "url_for_landing_page": best_location.get("url_for_landing_page")
            }

            # Repository information
            if best_location.get("host_type") == "repository":
                metrics["repository"] = {
                    "name": best_location.get("repository_name"),
                    "id": best_location.get("repository_id"),
                    "pmh_id": best_location.get("pmh_id")
                }

        # All OA locations
        oa_locations = oa_data.get("oa_locations", [])
        metrics["oa_location_count"] = len(oa_locations)

        # Group locations by type
        publisher_locations = []
        repository_locations = []

        for loc in oa_locations:
            location_info = {
                "url": loc.get("url"),
                "license": loc.get("license"),
                "version": loc.get("version")
            }

            if loc.get("host_type") == "publisher":
                publisher_locations.append(location_info)
            else:
                repository_locations.append(location_info)

        metrics["publisher_locations"] = publisher_locations
        metrics["repository_locations"] = repository_locations

        # Publication info
        metrics["publication"] = {
            "title": oa_data.get("title"),
            "year": oa_data.get("year"),
            "journal_name": oa_data.get("journal_name"),
            "journal_issn_l": oa_data.get("journal_issn_l"),
            "publisher": oa_data.get("publisher"),
            "published_date": oa_data.get("published_date"),
            "updated": oa_data.get("updated")
        }

        # Z-score (statistical measure of OA likelihood)
        metrics["z_authors"] = oa_data.get("z_authors")

        # Data availability
        metrics["data_standard"] = oa_data.get("data_standard")

        return metrics

    def classify_oa_status(self, oa_status: str) -> Dict[str, Any]:
        """
        Classify and explain OA status.

        Args:
            oa_status: Status from Unpaywall (gold, green, hybrid, bronze, closed)

        Returns:
            Classification with explanation and quality score
        """
        classifications = {
            "gold": {
                "label": "Gold Open Access",
                "description": "Published in fully OA journal",
                "quality_score": 1.0,
                "permanent": True,
                "has_license": True,
                "reuse_rights": "Full (with attribution)"
            },
            "green": {
                "label": "Green Open Access",
                "description": "Repository version available",
                "quality_score": 0.8,
                "permanent": True,
                "has_license": False,
                "reuse_rights": "Limited (check repository)"
            },
            "hybrid": {
                "label": "Hybrid Open Access",
                "description": "OA article in subscription journal",
                "quality_score": 0.9,
                "permanent": True,
                "has_license": True,
                "reuse_rights": "Full (with license)"
            },
            "bronze": {
                "label": "Bronze Open Access",
                "description": "Free to read, no license",
                "quality_score": 0.6,
                "permanent": False,
                "has_license": False,
                "reuse_rights": "Reading only"
            },
            "closed": {
                "label": "Closed Access",
                "description": "No free version available",
                "quality_score": 0.0,
                "permanent": False,
                "has_license": False,
                "reuse_rights": "None"
            }
        }

        return classifications.get(oa_status, classifications["closed"])

    def get_oa_score(self, oa_data: Dict[str, Any]) -> float:
        """
        Calculate an OA quality score.

        Args:
            oa_data: OA metrics from extract_oa_metrics()

        Returns:
            Score from 0-1 indicating OA quality
        """
        if not oa_data.get("is_oa"):
            return 0.0

        oa_status = oa_data.get("oa_status", "closed")
        classification = self.classify_oa_status(oa_status)
        base_score = classification["quality_score"]

        # Bonus for having license
        if oa_data.get("best_oa_location", {}).get("license"):
            base_score = min(base_score * 1.1, 1.0)

        # Bonus for being in DOAJ (Directory of Open Access Journals)
        if oa_data.get("journal_is_in_doaj"):
            base_score = min(base_score * 1.1, 1.0)

        # Bonus for having multiple locations
        if oa_data.get("oa_location_count", 0) > 1:
            base_score = min(base_score * 1.05, 1.0)

        return base_score

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make rate-limited request to Unpaywall API.

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

            if response.status_code == 404:
                logger.info(f"DOI not found in Unpaywall")
                return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Unpaywall API error: {e}")
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
    """Test Unpaywall client."""
    print("Testing Unpaywall Client...")

    # Initialize client
    client = UnpaywallClient(
        email="test@example.com",
        cache_dir=Path("cache/unpaywall")
    )

    # Test DOI lookup
    test_dois = [
        "10.1038/nature14016",  # Nature article
        "10.1371/journal.pone.0213154",  # PLOS ONE (gold OA)
        "10.1016/j.cell.2018.05.008"  # Cell (likely closed)
    ]

    for doi in test_dois:
        print(f"\n=== Checking OA status for: {doi} ===")
        oa_data = client.get_oa_status(doi)

        if oa_data:
            # Extract metrics
            metrics = client.extract_oa_metrics(oa_data)

            print(f"✅ Found: {metrics['publication']['title'][:60]}...")
            print(f"   Year: {metrics['publication']['year']}")
            print(f"   Journal: {metrics['publication']['journal_name']}")

            print(f"\n   OA Status: {metrics['oa_status']}")
            print(f"   Is OA: {metrics['is_oa']}")

            # Classify OA status
            classification = client.classify_oa_status(metrics['oa_status'])
            print(f"   Classification: {classification['label']}")
            print(f"   Description: {classification['description']}")
            print(f"   Quality Score: {classification['quality_score']}")
            print(f"   Reuse Rights: {classification['reuse_rights']}")

            # Calculate OA score
            oa_score = client.get_oa_score(metrics)
            print(f"   Overall OA Score: {oa_score:.2f}")

            if metrics.get("best_oa_location"):
                best = metrics["best_oa_location"]
                print(f"\n   Best OA Location:")
                print(f"      URL: {best['url'][:80]}...")
                print(f"      Type: {best['host_type']}")
                print(f"      License: {best.get('license', 'None')}")
                print(f"      Version: {best.get('version', 'Unknown')}")

            print(f"\n   Total OA Locations: {metrics['oa_location_count']}")
            print(f"   Publisher Locations: {len(metrics['publisher_locations'])}")
            print(f"   Repository Locations: {len(metrics['repository_locations'])}")

        else:
            print(f"❌ No OA data found")

    print("\n✅ Unpaywall client test complete")


if __name__ == "__main__":
    main()