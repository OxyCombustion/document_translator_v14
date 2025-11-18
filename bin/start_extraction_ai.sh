#!/bin/bash
# Start Extraction AI Session
# Loads: CLAUDE.md + CLAUDE_EXTRACTION.md
# Context: 798 lines (69% reduction from monolithic)

set -e

echo "📤 Starting Extraction AI Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Context Files Loading:"
echo "   - CLAUDE.md (418 lines)"
echo "   - CLAUDE_EXTRACTION.md (380 lines)"
echo "   Total: 798 lines (vs 2,611 monolithic)"
echo ""
echo "📤 Extraction AI Role:"
echo "   - Implement extraction pipeline features"
echo "   - Work with 7 extraction packages"
echo "   - Maintain extraction → RAG contract"
echo "   - Focus: PDF → Structured JSON"
echo ""
echo "📦 Packages in scope:"
echo "   - extraction_v14_P1 (core)"
echo "   - detection_v14_P14 (Docling)"
echo "   - docling_agents_v14_P17, P8 (agents)"
echo "   - specialized_extraction_v14_P15 (YOLO)"
echo "   - extraction_comparison_v14_P12"
echo "   - extraction_utilities_v14_P18"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to extraction pipeline directory
cd "$(dirname "$0")/../pipelines/extraction"

# Check context files exist
if [ ! -f "../../CLAUDE.md" ]; then
    echo "❌ Error: CLAUDE.md not found"
    exit 1
fi

if [ ! -f "CLAUDE_EXTRACTION.md" ]; then
    echo "❌ Error: CLAUDE_EXTRACTION.md not found"
    exit 1
fi

echo "✅ Context files validated"
echo ""
echo "💡 Extraction AI Ready!"
echo ""
echo "Example tasks:"
echo "  - 'How do I add PDF annotation extraction?'"
echo "  - 'Fix YOLO detection accuracy for equations.'"
echo "  - 'Update Docling integration to latest version.'"
echo ""

echo "📋 To manually load context in Claude Code:"
echo "   1. Open Claude Code"
echo "   2. Load: ../../CLAUDE.md"
echo "   3. Load: CLAUDE_EXTRACTION.md"
echo "   4. You now have extraction-focused context!"
echo ""
echo "🚀 Or use: claude-code --context=../../CLAUDE.md --context=CLAUDE_EXTRACTION.md"
echo ""

# Uncomment when Claude Code CLI supports context loading:
# claude-code --context=../../CLAUDE.md --context=CLAUDE_EXTRACTION.md

echo "Press Ctrl+C to exit"
read -r
