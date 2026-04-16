import sys
from pathlib import Path

# Add parent directory to path so sentinel_os can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentinel_os.core.system_simulator import SystemSimulator

def main():
    print("\n" + "="*70)
    print("  🔷 SentinelOS - AI-Advised AUV Operating System 🔷")
    print("="*70)
    print("\n🚀 Starting SentinelOS Simulation with AI Advisor...")
    
    simulator = SystemSimulator(enable_ai=True)
    simulator.initialize()
    simulator.run()
    
    # Print summary
    print("\n" + "="*70)
    print("  📊 SIMULATION SUMMARY")
    print("="*70)
    
    metrics = simulator.metrics
    resource_failures = sum(1 for f in metrics.faults if f["fault_type"] == "RESOURCE_FAILURE")
    deadline_misses = sum(1 for f in metrics.faults if f["fault_type"] == "DEADLINE_MISS")
    
    print(f"\n📈 METRICS:")
    print(f"   • Total Faults: {len(metrics.faults)}")
    print(f"   • Resource Failures: {resource_failures}")
    print(f"   • Deadline Misses: {deadline_misses}")
    print(f"   • Total Steps: {len(metrics.records)}")
    
    if simulator.ai_advisor:
        ai_stats = simulator.ai_advisor.get_advisor_stats()
        print(f"\n🤖 AI ADVISOR:")
        print(f"   • Model Loaded: {'✅ Yes' if ai_stats['model_loaded'] else '❌ No'}")
        print(f"   • Interventions: {ai_stats['interventions']}")
        print(f"   • Last Confidence: {ai_stats['last_confidence']:.1%}")
    
    print("\n✅ Simulation completed.\n")

if __name__ == "__main__":
    main()
