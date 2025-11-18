#!/bin/bash
# Start Shared Infrastructure AI Session
# Loads: CLAUDE.md + CLAUDE_SHARED.md
# Context: 847 lines (68% reduction from monolithic)

set -e

echo "🔧 Starting Shared Infrastructure AI Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Context Files Loading:"
echo "   - CLAUDE.md (418 lines)"
echo "   - CLAUDE_SHARED.md (429 lines)"
echo "   Total: 847 lines (vs 2,611 monolithic)"
echo ""
echo "🔧 Shared Infrastructure AI Role:"
echo "   - Implement shared foundation features"
echo "   - Work with 6 shared packages"
echo "   - Support all 3 pipelines"
echo "   - Focus: Common utilities, agents, CLI"
echo ""
echo "📦 Packages in scope:"
echo "   - common (base classes)"
echo "   - agent_infrastructure_v14_P8 (agents)"
echo "   - parallel_processing_v14_P9 (multi-core)"
echo "   - infrastructure_v14_P10 (sessions)"
echo "   - cli_v14_P7 (command-line)"
echo "   - specialized_utilities_v14_P20 (tools)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to shared pipeline directory
cd "$(dirname "$0")/../pipelines/shared"

# Check context files exist
if [ ! -f "../../CLAUDE.md" ]; then
    echo "❌ Error: CLAUDE.md not found"
    exit 1
fi

if [ ! -f "CLAUDE_SHARED.md" ]; then
    echo "❌ Error: CLAUDE_SHARED.md not found"
    exit 1
fi

echo "✅ Context files validated"
echo ""
echo "💡 Shared Infrastructure AI Ready!"
echo ""
echo "Example tasks:"
echo "  - 'How do I add a new base class to common?'"
echo "  - 'Optimize parallel processing for multi-core.'"
echo "  - 'Add new CLI command to orchestrator.'"
echo ""

echo "📋 To manually load context in Claude Code:"
echo "   1. Open Claude Code"
echo "   2. Load: ../../CLAUDE.md"
echo "   3. Load: CLAUDE_SHARED.md"
echo "   4. You now have infrastructure-focused context!"
echo ""
echo "🚀 Or use: claude-code --context=../../CLAUDE.md --context=CLAUDE_SHARED.md"
echo ""

# Uncomment when Claude Code CLI supports context loading:
# claude-code --context=../../CLAUDE.md --context=CLAUDE_SHARED.md

echo "Press Ctrl+C to exit"
read -r
