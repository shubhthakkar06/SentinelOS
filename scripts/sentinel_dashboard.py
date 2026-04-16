#!/usr/bin/env python3
"""
SentinelOS Dashboard - Real-time monitoring and analytics for AI advisor performance
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentinel_os.core.system_simulator import SystemSimulator
import json
from datetime import datetime


class Dashboard:
    """Real-time dashboard for SentinelOS monitoring"""
    
    def __init__(self):
        self.simulator = None
        
    def generate_ai_advisor_report(self, simulator):
        """Generate detailed AI advisor performance report"""
        print("\n" + "="*70)
        print("  🤖 AI ADVISOR PERFORMANCE REPORT")
        print("="*70)
        
        if not simulator.ai_advisor:
            print("❌ AI Advisor not initialized")
            return
        
        stats = simulator.ai_advisor.get_advisor_stats()
        metrics = simulator.metrics
        
        # Count fault types
        resource_failures = sum(1 for f in metrics.faults if f["fault_type"] == "RESOURCE_FAILURE")
        deadline_misses = sum(1 for f in metrics.faults if f["fault_type"] == "DEADLINE_MISS")
        
        print(f"\n📊 ADVISOR ACTIVITY:")
        print(f"   • Model Loaded: {'✅ Yes' if stats['model_loaded'] else '❌ No'}")
        print(f"   • Interventions Made: {stats['interventions']}")
        print(f"   • Last Confidence: {stats['last_confidence']:.1%}")
        
        print(f"\n📈 SYSTEM FAULTS:")
        print(f"   • Total Faults: {len(metrics.faults)}")
        print(f"   • Resource Failures: {resource_failures}")
        print(f"   • Deadline Misses: {deadline_misses}")
        
        if stats['interventions'] > 0:
            avg_intervention = stats['last_confidence']
            print(f"\n✨ IMPACT ANALYSIS:")
            print(f"   • Average Intervention Confidence: {avg_intervention:.1%}")
            print(f"   • Fault Rate: {len(metrics.faults) / max(1, len(metrics.records)):.2%}")
    
    def compare_baseline_vs_ai(self, seed=42):
        """Compare performance with and without AI"""
        print("\n" + "="*70)
        print("  📊 BASELINE VS AI-ADVISED COMPARISON")
        print("="*70)
        
        # Run baseline (no AI)
        print("\n🔄 Running Baseline (No AI Advisor)...")
        sim_baseline = SystemSimulator(enable_ai=False, seed=seed)
        sim_baseline.initialize()
        sim_baseline.run()
        
        baseline_metrics = sim_baseline.metrics
        baseline_rf = sum(1 for f in baseline_metrics.faults if f["fault_type"] == "RESOURCE_FAILURE")
        baseline_dm = sum(1 for f in baseline_metrics.faults if f["fault_type"] == "DEADLINE_MISS")
        
        # Run with AI
        print("🔄 Running AI-Advised Scheduler...")
        sim_ai = SystemSimulator(enable_ai=True, seed=seed)
        sim_ai.initialize()
        sim_ai.run()
        
        ai_metrics = sim_ai.metrics
        ai_rf = sum(1 for f in ai_metrics.faults if f["fault_type"] == "RESOURCE_FAILURE")
        ai_dm = sum(1 for f in ai_metrics.faults if f["fault_type"] == "DEADLINE_MISS")
        
        # Display comparison
        print("\n" + "-"*70)
        print(f"{'Metric':<30} {'Baseline':<15} {'AI-Advised':<15} {'Improvement':<10}")
        print("-"*70)
        
        # Total faults
        total_baseline = len(baseline_metrics.faults)
        total_ai = len(ai_metrics.faults)
        improvement = ((total_baseline - total_ai) / max(1, total_baseline)) * 100 if total_baseline > 0 else 0
        print(f"{'Total Faults':<30} {total_baseline:<15} {total_ai:<15} {improvement:>8.1f}%")
        
        # Resource failures
        rf_improvement = ((baseline_rf - ai_rf) / max(1, baseline_rf)) * 100 if baseline_rf > 0 else 0
        print(f"{'Resource Failures':<30} {baseline_rf:<15} {ai_rf:<15} {rf_improvement:>8.1f}%")
        
        # Deadline misses
        dm_improvement = ((baseline_dm - ai_dm) / max(1, baseline_dm)) * 100 if baseline_dm > 0 else 0
        print(f"{'Deadline Misses':<30} {baseline_dm:<15} {ai_dm:<15} {dm_improvement:>8.1f}%")
        
        print("-"*70)
        
        # AI Advisor stats
        if sim_ai.ai_advisor:
            ai_stats = sim_ai.ai_advisor.get_advisor_stats()
            print(f"{'AI Interventions':<30} {'N/A':<15} {ai_stats['interventions']:<15}")
        
        print("\n" + "="*70)
        if improvement > 0:
            print(f"✅ RESULT: AI Advisor reduced faults by {improvement:.1f}%!")
        else:
            print(f"⚠️  RESULT: Baseline performed better (differences may be small)")
        print("="*70)
        
        return {
            "baseline": {"total": total_baseline, "resource_failures": baseline_rf, "deadline_misses": baseline_dm},
            "ai": {"total": total_ai, "resource_failures": ai_rf, "deadline_misses": ai_dm},
            "improvement": improvement
        }
    
    def analyze_ai_recommendations(self, num_steps=500):
        """Analyze AI recommendation patterns"""
        print("\n" + "="*70)
        print("  📊 AI RECOMMENDATION ANALYSIS")
        print("="*70)
        
        sim = SystemSimulator(enable_ai=True, seed=42)
        sim.initialize()
        
        recommendations = {
            "URGENT_BOOST": 0,
            "STRONG_BOOST": 0,
            "MODERATE_BOOST": 0,
            "LIGHT_BOOST": 0,
            "MONITOR": 0,
        }
        
        confidence_values = []
        
        for _ in range(min(num_steps, sim.max_time)):
            # Generate events
            sim.event_manager.generate_events(sim.time)
            
            # Generate and add tasks
            new_tasks = sim.task_generator.generate_task(sim.time)
            sim.kernel.add_tasks(new_tasks)
            
            # Get next task and trigger AI analysis
            system_state = {"available_memory": sim.resource_manager.available_memory}
            task = sim.kernel.get_next_task(system_state)
            
            # Track recommendation
            if sim.ai_advisor and sim.ai_advisor.last_recommendation:
                rec = sim.ai_advisor.last_recommendation
                recommendations[rec.action] += 1
                confidence_values.append(sim.ai_advisor.last_confidence)
            
            # Execute task (simplified)
            if task:
                sim.resource_manager.allocate(task)
                sim.resource_manager.release(task)
                faults = sim.faults_injector.inject_task_fault(task, sim.time)
                for f in faults:
                    sim.metrics.record_fault(f)
            
            sim.time += 1
        
        # Display analysis
        print(f"\n📈 RECOMMENDATION DISTRIBUTION (over {len(confidence_values)} decisions):")
        total_recs = sum(recommendations.values())
        if total_recs > 0:
            for action, count in recommendations.items():
                pct = (count / total_recs) * 100
                bar = "█" * int(pct / 5)
                print(f"   {action:<15} {count:>3} ({pct:>5.1f}%) {bar}")
        
        if confidence_values:
            avg_conf = sum(confidence_values) / len(confidence_values)
            max_conf = max(confidence_values)
            min_conf = min(confidence_values)
            print(f"\n💡 CONFIDENCE STATISTICS:")
            print(f"   • Average: {avg_conf:.1%}")
            print(f"   • Maximum: {max_conf:.1%}")
            print(f"   • Minimum: {min_conf:.1%}")


def main():
    dashboard = Dashboard()
    
    import argparse
    parser = argparse.ArgumentParser(description="SentinelOS Dashboard")
    parser.add_argument("--compare", action="store_true", 
                       help="Compare baseline vs AI performance")
    parser.add_argument("--analyze-ai", action="store_true",
                       help="Analyze AI recommendation patterns")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility")
    
    args = parser.parse_args()
    
    if args.compare:
        dashboard.compare_baseline_vs_ai(seed=args.seed)
    elif args.analyze_ai:
        dashboard.analyze_ai_recommendations()
    else:
        print("\n❌ Use --compare or --analyze-ai flag")
        print("   Type: python sentinel_dashboard.py --help for options.\n")


if __name__ == "__main__":
    main()
