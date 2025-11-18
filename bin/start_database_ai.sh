#!/bin/bash
# Start Database AI Session
# Loads: CLAUDE.md + CLAUDE_DATABASE.md
# Context: 853 lines (67% reduction from monolithic)

set -e

echo "💾 Starting Database AI Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Context Files Loading:"
echo "   - CLAUDE.md (418 lines)"
echo "   - CLAUDE_DATABASE.md (435 lines)"
echo "   Total: 853 lines (vs 2,611 monolithic)"
echo ""
echo "💾 Database AI Role:"
echo "   - Implement database pipeline features"
echo "   - Work with 4 database packages"
echo "   - Maintain RAG → database contract"
echo "   - Focus: JSONL → Vector DB + Metadata"
echo ""
echo "📦 Packages in scope:"
echo "   - curation_v14_P3 (JSONL processing)"
echo "   - database_v14_P6 (ChromaDB/Pinecone)"
echo "   - metadata_v14_P13 (Zotero integration)"
echo "   - relationship_detection_v14_P5 (citations)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to database pipeline directory
cd "$(dirname "$0")/../pipelines/data_management"

# Check context files exist
if [ ! -f "../../CLAUDE.md" ]; then
    echo "❌ Error: CLAUDE.md not found"
    exit 1
fi

if [ ! -f "CLAUDE_DATABASE.md" ]; then
    echo "❌ Error: CLAUDE_DATABASE.md not found"
    exit 1
fi

echo "✅ Context files validated"
echo ""
echo "💡 Database AI Ready!"
echo ""
echo "Example tasks:"
echo "  - 'How do I add a new metadata field from Zotero?'"
echo "  - 'Optimize bulk insert performance for ChromaDB.'"
echo "  - 'Fix citation detection false positives.'"
echo ""

echo "📋 To manually load context in Claude Code:"
echo "   1. Open Claude Code"
echo "   2. Load: ../../CLAUDE.md"
echo "   3. Load: CLAUDE_DATABASE.md"
echo "   4. You now have database-focused context!"
echo ""
echo "🚀 Or use: claude-code --context=../../CLAUDE.md --context=CLAUDE_DATABASE.md"
echo ""

# Uncomment when Claude Code CLI supports context loading:
# claude-code --context=../../CLAUDE.md --context=CLAUDE_DATABASE.md

echo "Press Ctrl+C to exit"
read -r
