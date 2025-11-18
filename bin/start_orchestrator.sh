#!/bin/bash
# Start Orchestrator AI Session
# Loads: CLAUDE.md + ORCHESTRATOR.md
# Context: 1,104 lines (58% reduction from monolithic)

set -e

echo "🎯 Starting Orchestrator AI Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Context Files Loading:"
echo "   - CLAUDE.md (418 lines)"
echo "   - ORCHESTRATOR.md (686 lines)"
echo "   Total: 1,104 lines (vs 2,611 monolithic)"
echo ""
echo "🎯 Orchestrator Role:"
echo "   - System-wide coordination"
echo "   - Cross-pipeline task delegation"
echo "   - Data contract management"
echo "   - Integration oversight"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Check context files exist
if [ ! -f "CLAUDE.md" ]; then
    echo "❌ Error: CLAUDE.md not found"
    exit 1
fi

if [ ! -f "ORCHESTRATOR.md" ]; then
    echo "❌ Error: ORCHESTRATOR.md not found"
    exit 1
fi

echo "✅ Context files validated"
echo ""
echo "💡 Orchestrator AI Ready!"
echo ""
echo "Example tasks:"
echo "  - 'What pipelines exist and how do they integrate?'"
echo "  - 'I want to add annotation extraction. Create a task plan.'"
echo "  - 'Review the data contracts between pipelines.'"
echo ""

# Launch Claude Code with orchestrator context
# Note: Adjust this command based on your Claude Code installation
# For now, this is a placeholder showing the concept

echo "📋 To manually load context in Claude Code:"
echo "   1. Open Claude Code"
echo "   2. Load: CLAUDE.md"
echo "   3. Load: ORCHESTRATOR.md"
echo "   4. You now have orchestrator-level context!"
echo ""
echo "🚀 Or use: claude-code --context=CLAUDE.md --context=ORCHESTRATOR.md"
echo ""

# Uncomment when Claude Code CLI supports context loading:
# claude-code --context=CLAUDE.md --context=ORCHESTRATOR.md

echo "Press Ctrl+C to exit"
read -r
