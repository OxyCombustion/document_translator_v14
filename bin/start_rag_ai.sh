#!/bin/bash
# Start RAG AI Session
# Loads: CLAUDE.md + CLAUDE_RAG.md
# Context: 823 lines (68% reduction from monolithic)

set -e

echo "🔄 Starting RAG AI Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Context Files Loading:"
echo "   - CLAUDE.md (418 lines)"
echo "   - CLAUDE_RAG.md (405 lines)"
echo "   Total: 823 lines (vs 2,611 monolithic)"
echo ""
echo "🔄 RAG AI Role:"
echo "   - Implement RAG pipeline features"
echo "   - Work with 5 RAG packages"
echo "   - Maintain extraction → RAG → database contracts"
echo "   - Focus: JSON → JSONL + Knowledge Graph"
echo ""
echo "📦 Packages in scope:"
echo "   - rag_v14_P2 (core JSONL generation)"
echo "   - rag_extraction_v14_P16 (RAG-optimized)"
echo "   - semantic_processing_v14_P4 (analysis)"
echo "   - chunking_v14_P10 (semantic chunking)"
echo "   - analysis_validation_v14_P19 (validation)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to RAG pipeline directory
cd "$(dirname "$0")/../pipelines/rag_ingestion"

# Check context files exist
if [ ! -f "../../CLAUDE.md" ]; then
    echo "❌ Error: CLAUDE.md not found"
    exit 1
fi

if [ ! -f "CLAUDE_RAG.md" ]; then
    echo "❌ Error: CLAUDE_RAG.md not found"
    exit 1
fi

echo "✅ Context files validated"
echo ""
echo "💡 RAG AI Ready!"
echo ""
echo "Example tasks:"
echo "  - 'How do I optimize semantic chunking for equations?'"
echo "  - 'Add support for citation graph generation.'"
echo "  - 'Fix validation errors in JSONL output.'"
echo ""

echo "📋 To manually load context in Claude Code:"
echo "   1. Open Claude Code"
echo "   2. Load: ../../CLAUDE.md"
echo "   3. Load: CLAUDE_RAG.md"
echo "   4. You now have RAG-focused context!"
echo ""
echo "🚀 Or use: claude-code --context=../../CLAUDE.md --context=CLAUDE_RAG.md"
echo ""

# Uncomment when Claude Code CLI supports context loading:
# claude-code --context=../../CLAUDE.md --context=CLAUDE_RAG.md

echo "Press Ctrl+C to exit"
read -r
