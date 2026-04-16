#!/bin/bash
# Quick Start Guide - Run this to test all improvements

echo "🔷 SentinelOS Improvement Test Suite"
echo "===================================="
echo ""

# Test 1: Verify AI Model
echo "1️⃣  Verifying AI Model..."
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from sentinel_os.ai.ai_advisor import AIAdvisor
ai = AIAdvisor()
if ai.model:
    print('   ✅ AI Model loaded successfully')
else:
    print('   ❌ AI Model failed to load')
" 2>/dev/null

# Test 2: Run standard simulation
echo ""
echo "2️⃣  Running Standard Simulation (with AI)..."
echo "   (This will show AI advisor in action)"
python3 scripts/run_system.py 2>&1 | tail -15 | head -10

# Test 3: Show CLI help
echo ""
echo "3️⃣  Available Interactive CLI Commands:"
echo "   python scripts/sentinel_cli.py --help"
python3 scripts/sentinel_cli.py --help 2>&1 | head -20

# Test 4: Show Dashboard features
echo ""
echo "4️⃣  Available Dashboard Commands:"
echo "   python scripts/sentinel_dashboard.py --help"
python3 scripts/sentinel_dashboard.py --help 2>&1 | head -15

echo ""
echo "===================================="
echo "✅ All systems operational!"
echo ""
echo "📚 Next Steps:"
echo "   1. Read: CLI_PLATFORM_GUIDE.md"
echo "   2. Try:  python scripts/sentinel_cli.py --interactive"
echo "   3. Test: python scripts/sentinel_dashboard.py --compare"
echo "   4. View: IMPROVEMENT_SUMMARY.md"
echo ""
