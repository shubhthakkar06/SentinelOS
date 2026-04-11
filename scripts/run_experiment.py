import sys
import os
import io
import matplotlib.pyplot as plt
from sentinel_os.core.system_simulator import SystemSimulator

class HiddenPrints:
    """Context manager to suppress stdout to keep the experiment clean"""
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

def extract_metrics(simulator, run_name):
    total_faults = len(simulator.metrics.faults)
    resource_failures = len([f for f in simulator.metrics.faults if f['fault_type'] == 'RESOURCE_FAILURE'])
    deadline_misses = len([f for f in simulator.metrics.faults if f['fault_type'] == 'DEADLINE_MISS'])
    total_steps = len(simulator.metrics.records)
    
    return {
        "name": run_name,
        "total_faults": total_faults,
        "resource_failures": resource_failures,
        "deadline_misses": deadline_misses,
        "total_steps": total_steps
    }

def run_experiment(seed=42):
    print("=====================================================")
    print("🚀 EXPERIMENTAL EVALUATION: BASELINE VS ADAPTIVE AI")
    print("=====================================================")
    print(f"Random Seed        : {seed}")
    print("Simulation Length  : 500 ticks")
    print("\n[1/2] Running Baseline Scheduler (No AI)...")
    
    # RUN 1: Baseline (enable_ai=False)
    with HiddenPrints():
        sim_base = SystemSimulator(enable_ai=False, seed=seed)
        sim_base.initialize()
        sim_base.run()
    base_metrics = extract_metrics(sim_base, "Baseline (No AI)")
    print("      ✓ Baseline complete.")

    print("[2/2] Running Adaptive Scheduler (AI Enabled)...")
    
    # RUN 2: Adaptive (enable_ai=True)
    with HiddenPrints():
        sim_ai = SystemSimulator(enable_ai=True, seed=seed)
        sim_ai.initialize()
        sim_ai.run()
    ai_metrics = extract_metrics(sim_ai, "Adaptive (AI Enabled)")
    print("      ✓ Adaptive complete.\n")

    # Display Terminal Results Side by Side
    print("=====================================================")
    print("📊 EXPERIMENT RESULTS")
    print("=====================================================")
    print(f"{'Metric':<25} | {'Baseline':<10} | {'Adaptive (AI)':<15}")
    print("-" * 55)
    print(f"{'Total Faults':<25} | {base_metrics['total_faults']:<10} | {ai_metrics['total_faults']:<15}")
    print(f"{'  -> Resource Failures':<25} | {base_metrics['resource_failures']:<10} | {ai_metrics['resource_failures']:<15}")
    print(f"{'  -> Deadline Misses':<25} | {base_metrics['deadline_misses']:<10} | {ai_metrics['deadline_misses']:<15}")
    print("=====================================================\n")
    
    # Calculate Reduction Rate
    if base_metrics['total_faults'] > 0:
        improvement = ((base_metrics['total_faults'] - ai_metrics['total_faults']) / base_metrics['total_faults']) * 100
        reduction_txt = f"{improvement:.1f}% Reduction in Total System Faults!"
        print(f"⭐ CONCLUSION: The AI Advisor successfully achieved a {reduction_txt}")
    
    # Rendering Matplotlib Chart
    print("\nGenerating visual slide chart for presentation...")
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    categories = ['Total Faults', 'Resource Failures', 'Deadline Misses']
    base_vals = [base_metrics['total_faults'], base_metrics['resource_failures'], base_metrics['deadline_misses']]
    ai_vals = [ai_metrics['total_faults'], ai_metrics['resource_failures'], ai_metrics['deadline_misses']]
    
    bar_width = 0.35
    x = range(len(categories))
    
    ax.bar([i - bar_width/2 for i in x], base_vals, bar_width, label='Baseline (No AI)', color='crimson')
    ax.bar([i + bar_width/2 for i in x], ai_vals, bar_width, label='Adaptive (AI Enabled)', color='cyan')
    
    ax.set_ylabel('Number of Occurrences', fontsize=12)
    ax.set_title('SentinelOS Evaluation: Baseline vs Adaptive AI', fontsize=14, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11)
    ax.legend(fontsize=12)
    
    for i in x:
        ax.text(i - bar_width/2, base_vals[i] + 0.5, str(base_vals[i]), ha='center')
        ax.text(i + bar_width/2, ai_vals[i] + 0.5, str(ai_vals[i]), ha='center')
        
    plt.tight_layout()
    plt.savefig('data/experiment_results_chart.png', dpi=300)
    print("✅ Saved to 'data/experiment_results_chart.png'. You can add this image to your slide!")

if __name__ == "__main__":
    run_experiment(seed=42)
