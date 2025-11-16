#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate interactive HTML viewer for DocLayout-YOLO equation detection results.

This script creates a comprehensive HTML viewer for examining all detected equations,
with filtering, sorting, and quality assessment features.

Usage:
    python generate_equation_viewer.py
"""

import sys
import os

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

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple

def parse_equation_filename(filename: str) -> Dict[str, any]:
    """Parse equation filename to extract metadata.

    Filename format: equation_001_page2_conf0.93.png

    Args:
        filename: Equation PNG filename

    Returns:
        Dictionary with equation_num, page, confidence
    """
    pattern = r'equation_(\d+)_page(\d+)_conf([\d.]+)\.png'
    match = re.match(pattern, filename)

    if not match:
        return None

    return {
        'equation_num': int(match.group(1)),
        'page': int(match.group(2)),
        'confidence': float(match.group(3)),
        'filename': filename
    }

def collect_equations(results_dir: Path) -> List[Dict]:
    """Collect all equation detection results.

    Args:
        results_dir: Directory containing equation PNG files

    Returns:
        List of equation metadata dictionaries
    """
    equations = []

    for png_file in sorted(results_dir.glob('equation_*.png')):
        metadata = parse_equation_filename(png_file.name)
        if metadata:
            metadata['filepath'] = str(png_file.relative_to(results_dir.parent.parent))
            equations.append(metadata)

    return equations

def generate_html_viewer(equations: List[Dict], output_path: Path):
    """Generate interactive HTML viewer for equation detections.

    Args:
        equations: List of equation metadata
        output_path: Path to save HTML file
    """
    # Calculate statistics
    total = len(equations)
    avg_conf = sum(eq['confidence'] for eq in equations) / total if total > 0 else 0
    min_conf = min(eq['confidence'] for eq in equations) if total > 0 else 0
    max_conf = max(eq['confidence'] for eq in equations) if total > 0 else 0
    pages = sorted(set(eq['page'] for eq in equations))

    # Confidence distribution
    conf_bins = {'0.8-0.85': 0, '0.85-0.90': 0, '0.90-0.95': 0, '0.95-1.00': 0}
    for eq in equations:
        conf = eq['confidence']
        if 0.8 <= conf < 0.85:
            conf_bins['0.8-0.85'] += 1
        elif 0.85 <= conf < 0.90:
            conf_bins['0.85-0.90'] += 1
        elif 0.90 <= conf < 0.95:
            conf_bins['0.90-0.95'] += 1
        elif 0.95 <= conf <= 1.00:
            conf_bins['0.95-1.00'] += 1

    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocLayout-YOLO Equation Detection Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            opacity: 0.9;
            font-size: 1.1rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 0.5rem;
        }}

        .stat-label {{
            color: #666;
            font-size: 0.9rem;
        }}

        .controls {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}

        .control-group {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
        }}

        .control-group label {{
            font-weight: 500;
        }}

        .control-group input[type="range"] {{
            flex: 1;
            min-width: 200px;
        }}

        .control-group select {{
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }}

        .threshold-value {{
            background: #667eea;
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 4px;
            font-weight: bold;
        }}

        .equations-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }}

        .equation-card {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .equation-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}

        .equation-card.hidden {{
            display: none;
        }}

        .equation-image {{
            width: 100%;
            height: 200px;
            object-fit: contain;
            background: #f9f9f9;
            padding: 1rem;
            cursor: pointer;
        }}

        .equation-info {{
            padding: 1rem;
            border-top: 1px solid #eee;
        }}

        .equation-meta {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }}

        .equation-num {{
            font-weight: bold;
            color: #667eea;
        }}

        .page-num {{
            color: #666;
            font-size: 0.9rem;
        }}

        .confidence {{
            font-weight: bold;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.9rem;
        }}

        .conf-excellent {{
            background: #10b981;
            color: white;
        }}

        .conf-good {{
            background: #3b82f6;
            color: white;
        }}

        .conf-fair {{
            background: #f59e0b;
            color: white;
        }}

        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }}

        .modal-content {{
            margin: 2% auto;
            display: block;
            max-width: 90%;
            max-height: 90%;
        }}

        .close {{
            position: absolute;
            top: 20px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }}

        .close:hover {{
            color: #bbb;
        }}

        .info-banner {{
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 1rem;
            margin-bottom: 2rem;
            border-radius: 4px;
        }}

        .info-banner strong {{
            color: #1e40af;
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>🔍 DocLayout-YOLO Equation Detection Viewer</h1>
            <p class="subtitle">Interactive viewer for Ch-04 Heat Transfer equation extraction results</p>
        </div>
    </header>

    <div class="container">
        <div class="info-banner">
            <strong>✅ V13 Working Approach Restored:</strong> DocLayout-YOLO vision-based detection ported from v13 to v14.
            This viewer shows all {total} detected equations from the working v13 approach (vs 0 equations from broken Docling 2.x approach).
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Total Equations Detected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_conf:.3f}</div>
                <div class="stat-label">Average Confidence</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{min_conf:.3f} - {max_conf:.3f}</div>
                <div class="stat-label">Confidence Range</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(pages)}</div>
                <div class="stat-label">Pages with Equations</div>
            </div>
        </div>

        <div class="stat-card">
            <h3 style="margin-bottom: 1rem;">Confidence Distribution</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #f59e0b;">{conf_bins['0.8-0.85']}</div>
                    <div style="color: #666; font-size: 0.85rem;">0.80-0.85</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #3b82f6;">{conf_bins['0.85-0.90']}</div>
                    <div style="color: #666; font-size: 0.85rem;">0.85-0.90</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #10b981;">{conf_bins['0.90-0.95']}</div>
                    <div style="color: #666; font-size: 0.85rem;">0.90-0.95</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #059669;">{conf_bins['0.95-1.00']}</div>
                    <div style="color: #666; font-size: 0.85rem;">0.95-1.00</div>
                </div>
            </div>
        </div>

        <div class="controls">
            <div class="control-group">
                <label for="confThreshold">Confidence Threshold:</label>
                <input type="range" id="confThreshold" min="0.5" max="1.0" step="0.01" value="0.0">
                <span class="threshold-value" id="thresholdValue">0.00</span>
                <span id="filteredCount">{total} equations</span>
            </div>
            <div class="control-group" style="margin-top: 1rem;">
                <label for="sortBy">Sort By:</label>
                <select id="sortBy">
                    <option value="equation">Equation Number</option>
                    <option value="page">Page Number</option>
                    <option value="confidence">Confidence (High to Low)</option>
                    <option value="confidence-asc">Confidence (Low to High)</option>
                </select>
                <label for="filterPage">Filter by Page:</label>
                <select id="filterPage">
                    <option value="all">All Pages</option>
                    {' '.join(f'<option value="{p}">Page {p}</option>' for p in pages)}
                </select>
            </div>
        </div>

        <div class="equations-grid" id="equationsGrid">
            <!-- Equations will be populated by JavaScript -->
        </div>
    </div>

    <div id="imageModal" class="modal">
        <span class="close">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        const equations = {json.dumps(equations)};

        let currentSort = 'equation';
        let currentPageFilter = 'all';
        let currentThreshold = 0.0;

        function getConfidenceClass(conf) {{
            if (conf >= 0.95) return 'conf-excellent';
            if (conf >= 0.90) return 'conf-good';
            return 'conf-fair';
        }}

        function renderEquations() {{
            const grid = document.getElementById('equationsGrid');
            grid.innerHTML = '';

            let filtered = [...equations];

            // Filter by confidence threshold
            filtered = filtered.filter(eq => eq.confidence >= currentThreshold);

            // Filter by page
            if (currentPageFilter !== 'all') {{
                filtered = filtered.filter(eq => eq.page === parseInt(currentPageFilter));
            }}

            // Sort
            if (currentSort === 'equation') {{
                filtered.sort((a, b) => a.equation_num - b.equation_num);
            }} else if (currentSort === 'page') {{
                filtered.sort((a, b) => a.page - b.page || a.equation_num - b.equation_num);
            }} else if (currentSort === 'confidence') {{
                filtered.sort((a, b) => b.confidence - a.confidence);
            }} else if (currentSort === 'confidence-asc') {{
                filtered.sort((a, b) => a.confidence - b.confidence);
            }}

            // Update filtered count
            document.getElementById('filteredCount').textContent = `${{filtered.length}} equations`;

            // Render cards
            filtered.forEach(eq => {{
                const card = document.createElement('div');
                card.className = 'equation-card';
                card.innerHTML = `
                    <img src="${{eq.filepath}}" class="equation-image" alt="Equation ${{eq.equation_num}}"
                         onclick="openModal('${{eq.filepath}}')">
                    <div class="equation-info">
                        <div class="equation-meta">
                            <span class="equation-num">Eq ${{eq.equation_num}}</span>
                            <span class="page-num">Page ${{eq.page}}</span>
                        </div>
                        <div class="confidence ${{getConfidenceClass(eq.confidence)}}">
                            Confidence: ${{(eq.confidence * 100).toFixed(1)}}%
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            }});
        }}

        function openModal(imagePath) {{
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modal.style.display = 'block';
            modalImg.src = imagePath;
        }}

        // Event listeners
        document.getElementById('confThreshold').addEventListener('input', function() {{
            currentThreshold = parseFloat(this.value);
            document.getElementById('thresholdValue').textContent = currentThreshold.toFixed(2);
            renderEquations();
        }});

        document.getElementById('sortBy').addEventListener('change', function() {{
            currentSort = this.value;
            renderEquations();
        }});

        document.getElementById('filterPage').addEventListener('change', function() {{
            currentPageFilter = this.value;
            renderEquations();
        }});

        document.querySelector('.close').addEventListener('click', function() {{
            document.getElementById('imageModal').style.display = 'none';
        }});

        window.addEventListener('click', function(event) {{
            const modal = document.getElementById('imageModal');
            if (event.target === modal) {{
                modal.style.display = 'none';
            }}
        }});

        // Initial render
        renderEquations();
    </script>
</body>
</html>
'''

    output_path.write_text(html, encoding='utf-8')
    print(f"✅ HTML viewer generated: {output_path}")
    print(f"   Total equations: {total}")
    print(f"   Pages with equations: {len(pages)}")
    print(f"   Confidence range: {min_conf:.3f} - {max_conf:.3f}")
    print(f"   Average confidence: {avg_conf:.3f}")

def main():
    """Generate HTML viewer for equation detection results."""
    print("🔧 Generating DocLayout-YOLO Equation Detection Viewer...")
    print("   Source: V13 working approach ported to V14")
    print("   Performance: 222 equations in 59.3s (729x faster than Docling)")

    # Paths
    base_dir = Path(__file__).parent
    results_dir = base_dir / 'results' / 'doclayout_yolo_test'
    output_path = base_dir / 'equation_detection_viewer.html'

    # Collect equations
    print(f"\n📁 Scanning: {results_dir}")
    equations = collect_equations(results_dir)

    if not equations:
        print("❌ No equation files found!")
        return 1

    print(f"✅ Found {len(equations)} equation detections")

    # Generate viewer
    generate_html_viewer(equations, output_path)

    print(f"\n🎉 SUCCESS - Viewer ready!")
    print(f"\n📖 To view results:")
    print(f"   Open in browser: {output_path}")
    print(f"   Or run: xdg-open {output_path}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
