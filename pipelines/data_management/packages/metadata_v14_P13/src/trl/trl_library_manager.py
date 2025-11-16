# -*- coding: utf-8 -*-
"""
Technology TRL Library Manager

Manages persistent Technology Readiness Level (TRL) library for technologies.
Analogous to SymbolLibraryManager but for technology maturity assessments.

Architecture:
- Persistent knowledge base of technologies and their TRL assessments
- Multiple authoritative sources (Global CCS Institute, IEA, DOE, EU)
- Multi-source reconciliation with weighted consensus
- Uncertainty mapping (TRL → CAPEX/OPEX uncertainty)
- Document comparison (paper claims vs library consensus)

Author: TRL Library System
Created: 2025-01-15
Version: 1.0.0
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TRLAssessment:
    """Single TRL assessment from a source."""
    assessment_id: str
    date: str
    source: str
    report: str
    url: str
    source_type: str  # government_agency, research_consortium, academic, etc.
    credibility_weight: float  # 0-1
    trl: int
    trl_range: Optional[List[int]] = None
    application_context: str = ""
    geographic_scope: str = ""
    assessment_method: str = ""
    key_findings: str = ""
    limitations: str = ""
    extracted_text: str = ""
    component_trls: Optional[Dict[str, int]] = None


@dataclass
class TRLConsensus:
    """Reconciled consensus from multiple assessments."""
    trl: int
    trl_range: List[int]
    confidence: str  # low, medium, high
    last_updated: str
    assessment_basis: str
    disagreement_level: str  # low, medium, high, very_high
    recommended_for_planning: int
    rationale: str


class TRLLibraryManager:
    """
    Manages Technology TRL Library.

    Directory structure:
        technology_trl_library/
        ├── config/
        │   ├── schema_version.json
        │   ├── source_credibility.json
        │   └── uncertainty_mappings.json
        ├── technologies/
        │   ├── all_technologies.json
        │   └── carbon_capture/
        │       ├── oxyfuel_combustion.json
        │       └── ...
        ├── indices/
        │   ├── by_technology_name.json
        │   ├── by_alias.json
        │   └── by_domain.json
        └── metadata/
            └── library_stats.json
    """

    def __init__(self, library_root: Path = None):
        """
        Initialize TRL Library Manager.

        Args:
            library_root: Root directory for TRL library
                         Default: E:\document_translator_v13\technology_trl_library
        """
        if library_root is None:
            library_root = Path(__file__).parent.parent.parent.parent / "technology_trl_library"

        self.library_root = Path(library_root)
        self.config_dir = self.library_root / "config"
        self.tech_dir = self.library_root / "technologies"
        self.indices_dir = self.library_root / "indices"
        self.metadata_dir = self.library_root / "metadata"

        # Load configuration
        self._load_configuration()

    def _load_configuration(self):
        """Load library configuration files."""
        # Source credibility weights
        self.source_weights = {
            "intergovernmental_agency": 0.90,  # IEA, IEAGHG
            "research_consortium": 0.95,       # Global CCS Institute
            "government_agency": 0.85,         # DOE, EU Commission
            "academic_peer_reviewed": 0.60,    # Journal papers
            "industry_report": 0.70,           # Vendor reports
            "project_documentation": 0.75      # Demonstration projects
        }

        # TRL → Uncertainty mappings (NASA/DOE standard)
        self.uncertainty_map = {
            1: {"capex": 2.00, "opex": 2.00, "years": "8-12"},  # ±200%
            2: {"capex": 1.50, "opex": 1.50, "years": "7-10"},  # ±150%
            3: {"capex": 1.00, "opex": 1.00, "years": "6-9"},   # ±100%
            4: {"capex": 0.75, "opex": 0.60, "years": "5-7"},   # ±75%
            5: {"capex": 0.50, "opex": 0.45, "years": "4-6"},   # ±50%
            6: {"capex": 0.35, "opex": 0.30, "years": "2-4"},   # ±35%
            7: {"capex": 0.25, "opex": 0.20, "years": "1-3"},   # ±25%
            8: {"capex": 0.15, "opex": 0.12, "years": "0-2"},   # ±15%
            9: {"capex": 0.08, "opex": 0.06, "years": "0-1"}    # ±8%
        }

    def initialize_library(self):
        """Create library directory structure."""
        # Create directories
        self.library_root.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
        self.tech_dir.mkdir(exist_ok=True)
        (self.tech_dir / "carbon_capture").mkdir(exist_ok=True)
        self.indices_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)

        # Initialize indices
        self._save_json(self.indices_dir / "by_technology_name.json", {})
        self._save_json(self.indices_dir / "by_alias.json", {})
        self._save_json(self.indices_dir / "by_domain.json", {})

        # Initialize stats
        stats = {
            "total_technologies": 0,
            "total_assessments": 0,
            "last_updated": datetime.now().isoformat(),
            "library_version": "1.0.0"
        }
        self._save_json(self.metadata_dir / "library_stats.json", stats)

        print(f"✅ TRL Library initialized at: {self.library_root}")

    def add_technology(self, tech_data: Dict) -> str:
        """
        Add new technology to library.

        Args:
            tech_data: Technology data dictionary

        Returns:
            technology_id
        """
        tech_id = tech_data["technology_id"]
        domain = tech_data["domain"]
        canonical_name = tech_data["canonical_name"]

        # Save technology file
        domain_dir = self.tech_dir / domain
        domain_dir.mkdir(exist_ok=True)

        tech_file = domain_dir / f"{tech_id.replace('tech_', '').replace('_', '-')}.json"
        self._save_json(tech_file, tech_data)

        # Update indices
        self._update_indices(tech_data)

        # Update stats
        self._update_stats()

        print(f"✅ Added technology: {canonical_name} ({tech_id})")
        return tech_id

    def lookup_by_name(self, name: str) -> Optional[Dict]:
        """
        Look up technology by name.

        Args:
            name: Technology name (canonical or alias)

        Returns:
            Technology data or None
        """
        # Normalize name
        normalized = name.lower().strip()

        # Try exact match in name index
        name_index = self._load_json(self.indices_dir / "by_technology_name.json")
        if normalized in name_index:
            return self._load_technology(name_index[normalized])

        # Try alias index
        alias_index = self._load_json(self.indices_dir / "by_alias.json")
        if normalized in alias_index:
            return self._load_technology(alias_index[normalized])

        # Try partial match
        for tech_name, tech_id in name_index.items():
            if normalized in tech_name or tech_name in normalized:
                return self._load_technology(tech_id)

        return None

    def reconcile_assessments(self, assessments: List[TRLAssessment]) -> TRLConsensus:
        """
        Reconcile multiple TRL assessments using weighted consensus.

        Args:
            assessments: List of TRL assessments

        Returns:
            TRLConsensus object
        """
        if not assessments:
            return None

        if len(assessments) == 1:
            assessment = assessments[0]
            return TRLConsensus(
                trl=assessment.trl,
                trl_range=assessment.trl_range or [assessment.trl, assessment.trl],
                confidence="low",
                last_updated=datetime.now().isoformat(),
                assessment_basis="Single source only",
                disagreement_level="none",
                recommended_for_planning=assessment.trl,
                rationale=f"Single assessment from {assessment.source}"
            )

        # Calculate weighted scores
        weighted_scores = []
        for assessment in assessments:
            weight = assessment.credibility_weight
            weighted_scores.append({
                "trl": assessment.trl,
                "weight": weight,
                "source": assessment.source
            })

        # Statistics
        trls = [a.trl for a in assessments]
        weights = [a.credibility_weight for a in assessments]
        total_weight = sum(weights)

        # Weighted mean
        weighted_mean = sum(t * w for t, w in zip(trls, weights)) / total_weight

        # Weighted median
        sorted_pairs = sorted(zip(trls, weights))
        cumulative = 0
        weighted_median = sorted_pairs[0][0]
        for trl, weight in sorted_pairs:
            cumulative += weight
            if cumulative >= total_weight / 2:
                weighted_median = trl
                break

        # Range and disagreement
        trl_min = min(trls)
        trl_max = max(trls)
        trl_range_span = trl_max - trl_min

        if trl_range_span >= 4:
            disagreement = "very_high"
        elif trl_range_span == 3:
            disagreement = "high"
        elif trl_range_span == 2:
            disagreement = "medium"
        else:
            disagreement = "low"

        # Recommended TRL (conservative for high disagreement)
        if disagreement in ["very_high", "high"]:
            recommended = min(int(weighted_median), int(weighted_mean - 0.5 * trl_range_span))
        else:
            recommended = int(round(weighted_median))

        # Confidence
        if disagreement in ["very_high", "high"] or len(assessments) < 3:
            confidence = "low"
        elif disagreement == "medium" and len(assessments) >= 3:
            confidence = "medium"
        else:
            confidence = "high"

        # Rationale
        mode = max(set(trls), key=trls.count)
        mode_count = trls.count(mode)

        rationale_parts = []
        if mode_count >= len(trls) / 2:
            rationale_parts.append(f"Strong convergence at TRL {mode} ({mode_count}/{len(trls)} sources)")
        if disagreement in ["very_high", "high"]:
            rationale_parts.append(f"High disagreement ({trl_range_span} TRL levels) - using conservative estimate")

        highest_weight_assessment = max(assessments, key=lambda a: a.credibility_weight)
        rationale_parts.append(f"Highest credibility source ({highest_weight_assessment.source}) assessed TRL {highest_weight_assessment.trl}")

        return TRLConsensus(
            trl=recommended,
            trl_range=[trl_min, trl_max],
            confidence=confidence,
            last_updated=datetime.now().isoformat(),
            assessment_basis=f"Multi-source reconciliation from {len(assessments)} authoritative assessments",
            disagreement_level=disagreement,
            recommended_for_planning=recommended,
            rationale=". ".join(rationale_parts)
        )

    def get_uncertainty_mapping(self, trl: int, trl_range: List[int] = None) -> Dict:
        """
        Get CAPEX/OPEX uncertainty estimates for TRL.

        Args:
            trl: Technology Readiness Level
            trl_range: Optional range for pessimistic/optimistic bounds

        Returns:
            Uncertainty estimates dictionary
        """
        nominal = self.uncertainty_map.get(trl, self.uncertainty_map[5])

        if trl_range:
            pessimistic = self.uncertainty_map.get(trl_range[0], nominal)
            optimistic = self.uncertainty_map.get(trl_range[1], nominal)
        else:
            pessimistic = nominal
            optimistic = nominal

        return {
            "trl_basis": trl,
            "capex": {
                "uncertainty_nominal": f"±{int(nominal['capex'] * 100)}%",
                "uncertainty_pessimistic": f"±{int(pessimistic['capex'] * 100)}%",
                "uncertainty_optimistic": f"±{int(optimistic['capex'] * 100)}%",
                "basis": "NASA/DOE TRL standard uncertainty mappings"
            },
            "opex": {
                "uncertainty_nominal": f"±{int(nominal['opex'] * 100)}%",
                "uncertainty_pessimistic": f"±{int(pessimistic['opex'] * 100)}%",
                "uncertainty_optimistic": f"±{int(optimistic['opex'] * 100)}%"
            },
            "schedule": {
                "years_to_commercial": nominal["years"],
                "confidence": "medium" if trl >= 6 else "low"
            }
        }

    def _update_indices(self, tech_data: Dict):
        """Update search indices."""
        tech_id = tech_data["technology_id"]
        canonical = tech_data["canonical_name"].lower()
        aliases = [a.lower() for a in tech_data.get("aliases", [])]
        domain = tech_data["domain"]

        # Name index
        name_index = self._load_json(self.indices_dir / "by_technology_name.json")
        name_index[canonical] = tech_id
        self._save_json(self.indices_dir / "by_technology_name.json", name_index)

        # Alias index
        alias_index = self._load_json(self.indices_dir / "by_alias.json")
        for alias in aliases:
            alias_index[alias] = tech_id
        self._save_json(self.indices_dir / "by_alias.json", alias_index)

        # Domain index
        domain_index = self._load_json(self.indices_dir / "by_domain.json")
        if domain not in domain_index:
            domain_index[domain] = []
        if tech_id not in domain_index[domain]:
            domain_index[domain].append(tech_id)
        self._save_json(self.indices_dir / "by_domain.json", domain_index)

    def _update_stats(self):
        """Update library statistics."""
        stats = self._load_json(self.metadata_dir / "library_stats.json")

        # Count technologies
        tech_count = 0
        assessment_count = 0
        for domain_dir in self.tech_dir.iterdir():
            if domain_dir.is_dir():
                for tech_file in domain_dir.glob("*.json"):
                    tech_count += 1
                    tech_data = self._load_json(tech_file)
                    assessment_count += len(tech_data.get("assessments", []))

        stats["total_technologies"] = tech_count
        stats["total_assessments"] = assessment_count
        stats["last_updated"] = datetime.now().isoformat()

        self._save_json(self.metadata_dir / "library_stats.json", stats)

    def _load_technology(self, tech_id: str) -> Optional[Dict]:
        """Load technology by ID."""
        for domain_dir in self.tech_dir.iterdir():
            if domain_dir.is_dir():
                for tech_file in domain_dir.glob("*.json"):
                    tech_data = self._load_json(tech_file)
                    if tech_data.get("technology_id") == tech_id:
                        return tech_data
        return None

    def _load_json(self, path: Path) -> Dict:
        """Load JSON file."""
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json(self, path: Path, data: Dict):
        """Save JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Test initialization
    manager = TRLLibraryManager()
    manager.initialize_library()
    print("✅ TRL Library Manager initialized successfully")
