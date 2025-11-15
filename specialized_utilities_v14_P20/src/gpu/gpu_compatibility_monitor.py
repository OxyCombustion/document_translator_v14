"""
GPU Compatibility Monitor Agent
Monitors and reports AI framework compatibility with Intel Arc GPUs
Version: 1.0.0
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib


@dataclass
class GPUProfile:
    """GPU hardware profile."""
    model: str
    vram_gb: int
    architecture: str
    compute_units: Optional[int] = None
    ai_tops: Optional[int] = None
    driver_version: Optional[str] = None


@dataclass
class FrameworkCompatibility:
    """AI framework compatibility status."""
    framework_name: str
    version: str
    gpu_support: str  # "native" | "via_adapter" | "unsupported" | "unknown"
    accelerator: str
    installation_cmd: str
    vram_requirements: Dict[str, int]
    configuration_options: List[str]
    performance_notes: str
    last_verified: str
    source_urls: List[str]


@dataclass
class ModelCompatibility:
    """AI model compatibility with GPU."""
    model_name: str
    model_type: str  # "VLM" | "LLM" | "Diffusion" | "OCR"
    parameters: str
    vram_requirements: Dict[str, int]
    quantization_options: List[str]
    framework_support: List[str]
    gpu_compatible: bool
    performance_estimate: str
    source_urls: List[str]


class GPUCompatibilityMonitor:
    """Monitor GPU compatibility for AI frameworks and models."""

    def __init__(self, cache_dir: Optional[Path] = None, cache_days: int = 7):
        """
        Initialize GPU Compatibility Monitor.

        Args:
            cache_dir: Directory for compatibility cache (default: ./cache)
            cache_days: Number of days to cache results (default: 7)
        """
        self.cache_dir = cache_dir or Path("./cache/gpu_compatibility")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_duration = timedelta(days=cache_days)

    def _get_cache_key(self, query_type: str, params: Dict[str, Any]) -> str:
        """Generate cache key from query parameters."""
        params_str = json.dumps(params, sort_keys=True)
        hash_obj = hashlib.md5(params_str.encode())
        return f"{query_type}_{hash_obj.hexdigest()}.json"

    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Load data from cache if valid."""
        cache_file = self.cache_dir / cache_key
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cache_time = datetime.fromisoformat(data.get('cached_at'))
            if datetime.now() - cache_time < self.cache_duration:
                return data.get('result')
        except Exception:
            pass

        return None

    def _save_to_cache(self, cache_key: str, result: Any):
        """Save result to cache."""
        cache_file = self.cache_dir / cache_key
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'result': result
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)

    def check_framework_compatibility(
        self,
        framework_name: str,
        gpu_profile: GPUProfile,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Check framework compatibility with specified GPU.

        This method returns a compatibility check request that should be
        executed using web search tools.

        Args:
            framework_name: Name of AI framework (e.g., "Docling")
            gpu_profile: GPU hardware profile
            force_refresh: Bypass cache and search fresh data

        Returns:
            Dict containing search queries and cache info
        """
        cache_key = self._get_cache_key('framework', {
            'framework': framework_name,
            'gpu_model': gpu_profile.model,
            'vram': gpu_profile.vram_gb
        })

        # Check cache
        if not force_refresh:
            cached = self._load_from_cache(cache_key)
            if cached:
                return {
                    'status': 'cached',
                    'cache_key': cache_key,
                    'data': cached
                }

        # Generate search queries
        current_year = datetime.now().year
        current_month = datetime.now().strftime('%B')

        queries = [
            f"{framework_name} Intel Arc {gpu_profile.model} compatibility {current_year}",
            f"{framework_name} OpenVINO DirectML oneAPI support {current_year}",
            f"{framework_name} VRAM requirements configuration {current_year}",
            f"{framework_name} Intel GPU acceleration setup guide",
            f"{framework_name} {gpu_profile.vram_gb}GB VRAM configuration"
        ]

        return {
            'status': 'search_required',
            'cache_key': cache_key,
            'framework': framework_name,
            'gpu': asdict(gpu_profile),
            'queries': queries,
            'search_instructions': (
                f"Search for {framework_name} compatibility with {gpu_profile.model}. "
                f"Focus on: (1) GPU support status, (2) Accelerator framework (OpenVINO/DirectML/oneAPI), "
                f"(3) Installation commands, (4) VRAM requirements and configuration options, "
                f"(5) Performance characteristics"
            )
        }

    def find_compatible_models(
        self,
        model_type: str,
        gpu_profile: GPUProfile,
        max_vram_gb: Optional[int] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Find AI models compatible with GPU constraints.

        Args:
            model_type: Type of model ("VLM" | "LLM" | "Diffusion" | "OCR")
            gpu_profile: GPU hardware profile
            max_vram_gb: Maximum VRAM to use (defaults to gpu_profile.vram_gb)
            force_refresh: Bypass cache and search fresh data

        Returns:
            Dict containing search queries and cache info
        """
        vram_limit = max_vram_gb or gpu_profile.vram_gb

        cache_key = self._get_cache_key('models', {
            'model_type': model_type,
            'gpu_model': gpu_profile.model,
            'vram_limit': vram_limit
        })

        # Check cache
        if not force_refresh:
            cached = self._load_from_cache(cache_key)
            if cached:
                return {
                    'status': 'cached',
                    'cache_key': cache_key,
                    'data': cached
                }

        # Generate search queries
        current_year = datetime.now().year

        model_type_names = {
            'VLM': 'vision language models multimodal',
            'LLM': 'large language models',
            'Diffusion': 'stable diffusion image generation',
            'OCR': 'optical character recognition'
        }

        type_name = model_type_names.get(model_type, model_type)

        queries = [
            f"{type_name} {vram_limit}GB VRAM Intel Arc {current_year}",
            f"quantized {type_name} Intel Arc GPU {current_year}",
            f"{type_name} 4-bit 8-bit quantization VRAM requirements",
            f"best {type_name} {vram_limit}GB VRAM {current_year}",
            f"{type_name} inference Intel Arc B580"
        ]

        return {
            'status': 'search_required',
            'cache_key': cache_key,
            'model_type': model_type,
            'gpu': asdict(gpu_profile),
            'vram_limit': vram_limit,
            'queries': queries,
            'search_instructions': (
                f"Search for {type_name} compatible with {gpu_profile.model} ({vram_limit}GB VRAM). "
                f"Focus on: (1) Model names and parameter counts, (2) VRAM requirements per quantization level, "
                f"(3) Framework support (PyTorch/ONNX/etc), (4) Performance estimates (tokens/sec or time/image), "
                f"(5) Installation and configuration steps"
            )
        }

    def save_compatibility_result(
        self,
        cache_key: str,
        result: Dict[str, Any]
    ):
        """
        Save compatibility check result to cache.

        Args:
            cache_key: Cache key from check_framework_compatibility or find_compatible_models
            result: Compatibility data to cache
        """
        self._save_to_cache(cache_key, result)

    def generate_compatibility_report(
        self,
        gpu_profile: GPUProfile,
        frameworks_data: Optional[List[Dict]] = None,
        models_data: Optional[List[Dict]] = None,
        output_format: str = "markdown"
    ) -> str:
        """
        Generate comprehensive compatibility report.

        Args:
            gpu_profile: GPU hardware profile
            frameworks_data: List of framework compatibility results
            models_data: List of model compatibility results
            output_format: "markdown" | "json"

        Returns:
            Formatted compatibility report
        """
        if output_format == "json":
            return json.dumps({
                'gpu_profile': asdict(gpu_profile),
                'frameworks': frameworks_data or [],
                'models': models_data or [],
                'report_date': datetime.now().isoformat(),
                'cache_valid_until': (datetime.now() + self.cache_duration).isoformat()
            }, indent=2)

        # Markdown format
        report = []
        report.append(f"# GPU Compatibility Report")
        report.append(f"**GPU:** {gpu_profile.model} ({gpu_profile.vram_gb}GB VRAM)")
        if gpu_profile.architecture:
            report.append(f"**Architecture:** {gpu_profile.architecture}")
        if gpu_profile.driver_version:
            report.append(f"**Driver:** {gpu_profile.driver_version}")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Framework compatibility section
        if frameworks_data:
            report.append("## Framework Compatibility")
            report.append("")

            for fw in frameworks_data:
                status_icon = "✅" if fw.get('gpu_support') in ['native', 'via_adapter'] else "❌"
                report.append(f"### {status_icon} {fw.get('framework_name', 'Unknown')}")
                report.append(f"- **Status:** {fw.get('gpu_support', 'unknown')}")
                report.append(f"- **Accelerator:** {fw.get('accelerator', 'N/A')}")

                if fw.get('installation_cmd'):
                    report.append(f"- **Installation:** `{fw['installation_cmd']}`")

                vram = fw.get('vram_requirements', {})
                if vram:
                    vram_min = vram.get('minimum', 'N/A')
                    vram_rec = vram.get('recommended', 'N/A')
                    report.append(f"- **VRAM:** {vram_min}GB minimum, {vram_rec}GB recommended")

                if fw.get('configuration_options'):
                    report.append(f"- **Configuration Options:**")
                    for opt in fw['configuration_options']:
                        report.append(f"  - {opt}")

                if fw.get('performance_notes'):
                    report.append(f"- **Performance:** {fw['performance_notes']}")

                if fw.get('source_urls'):
                    report.append(f"- **Sources:** {', '.join(fw['source_urls'][:2])}")

                report.append("")

        # Models compatibility section
        if models_data:
            report.append("## Compatible Models")
            report.append("")

            # Group by model type
            model_types = {}
            for model in models_data:
                mtype = model.get('model_type', 'Other')
                if mtype not in model_types:
                    model_types[mtype] = []
                model_types[mtype].append(model)

            for mtype, models in model_types.items():
                type_names = {
                    'VLM': 'Vision-Language Models',
                    'LLM': 'Large Language Models',
                    'Diffusion': 'Image Generation Models',
                    'OCR': 'OCR Models'
                }
                report.append(f"### {type_names.get(mtype, mtype)}")
                report.append("")

                for i, model in enumerate(models, 1):
                    compat_icon = "✅" if model.get('gpu_compatible') else "⚠️"
                    report.append(f"{i}. **{compat_icon} {model.get('model_name', 'Unknown')}**")

                    if model.get('parameters'):
                        report.append(f"   - Parameters: {model['parameters']}")

                    vram = model.get('vram_requirements', {})
                    if vram:
                        vram_str = ', '.join([f"{k}: {v}GB" for k, v in vram.items()])
                        report.append(f"   - VRAM: {vram_str}")

                    if model.get('quantization_options'):
                        quant_str = ', '.join(model['quantization_options'])
                        report.append(f"   - Quantization: {quant_str}")

                    if model.get('performance_estimate'):
                        report.append(f"   - Performance: {model['performance_estimate']}")

                    if model.get('framework_support'):
                        fw_str = ', '.join(model['framework_support'])
                        report.append(f"   - Frameworks: {fw_str}")

                    report.append("")

        report.append("---")
        report.append(f"*Report valid until {(datetime.now() + self.cache_duration).strftime('%Y-%m-%d')}*")
        report.append(f"*Use `force_refresh=True` to update compatibility data*")

        return '\n'.join(report)

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached compatibility data."""
        cache_files = list(self.cache_dir.glob("*.json"))

        info = {
            'cache_directory': str(self.cache_dir),
            'cache_duration_days': self.cache_duration.days,
            'total_cached_items': len(cache_files),
            'cached_items': []
        }

        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                cache_time = datetime.fromisoformat(data.get('cached_at'))
                is_valid = datetime.now() - cache_time < self.cache_duration

                info['cached_items'].append({
                    'file': cache_file.name,
                    'cached_at': data.get('cached_at'),
                    'valid': is_valid,
                    'expires_at': (cache_time + self.cache_duration).isoformat()
                })
            except Exception:
                continue

        return info

    def clear_cache(self, older_than_days: Optional[int] = None):
        """
        Clear compatibility cache.

        Args:
            older_than_days: Clear only items older than N days (default: clear all)
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        deleted_count = 0

        for cache_file in cache_files:
            should_delete = False

            if older_than_days is None:
                should_delete = True
            else:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    cache_time = datetime.fromisoformat(data.get('cached_at'))
                    if datetime.now() - cache_time > timedelta(days=older_than_days):
                        should_delete = True
                except Exception:
                    should_delete = True  # Delete corrupted cache

            if should_delete:
                cache_file.unlink()
                deleted_count += 1

        return {
            'deleted_count': deleted_count,
            'remaining_count': len(list(self.cache_dir.glob("*.json")))
        }


# Convenience function for quick checks
def quick_gpu_check(
    gpu_model: str = "Intel Arc B580",
    vram_gb: int = 12,
    framework: Optional[str] = None,
    model_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick GPU compatibility check.

    Args:
        gpu_model: GPU model name
        vram_gb: GPU VRAM in GB
        framework: Optional framework to check
        model_type: Optional model type to search

    Returns:
        Compatibility check request
    """
    monitor = GPUCompatibilityMonitor()
    gpu = GPUProfile(
        model=gpu_model,
        vram_gb=vram_gb,
        architecture="Xe2 Battlemage" if "B580" in gpu_model else "Unknown"
    )

    results = {}

    if framework:
        results['framework'] = monitor.check_framework_compatibility(framework, gpu)

    if model_type:
        results['models'] = monitor.find_compatible_models(model_type, gpu)

    if not framework and not model_type:
        results['info'] = {
            'message': 'Specify framework or model_type for compatibility check',
            'gpu': asdict(gpu)
        }

    return results
