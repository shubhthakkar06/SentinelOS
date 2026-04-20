# SentinelOS

**AI-Advised Microkernel Operating System for Autonomous Underwater Vehicles (AUVs)**

> A real-time OS simulation implementing four scheduling algorithms, a physics-informed fault model, the Priority Inheritance Protocol (PIP), and an ML-based fault advisor — benchmarked with quantified results.

---

## Why AUVs?

Autonomous underwater vehicles cannot be rebooted mid-mission. A fault in the navigation task while the vehicle is at 200m depth is catastrophic. This makes AUV software a textbook application of hard real-time OS principles:

- **Hard deadlines** — sonar pings and depth control cannot miss their windows
- **Finite energy** — battery consumption determines mission duration
- **Fault isolation** — a fault in logging must not cascade to navigation
- **Priority correctness** — a critical task must never be inadvertently starved

SentinelOS simulates the OS kernel layer that enforces these guarantees.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SystemSimulator                       │
│  (simulation loop, event generation, task lifecycle)    │
└────────┬──────────────┬──────────────┬──────────────────┘
         │              │              │
    ┌────▼────┐   ┌─────▼────┐  ┌─────▼──────────┐
    │ Kernel  │   │ Resource │  │  LockManager   │
    │         │   │ Manager  │  │ (Priority      │
    │scheduler│   │mem+energy│  │  Inheritance)  │
    └────┬────┘   └──────────┘  └────────────────┘
         │
    ┌────▼─────────────────────────────────────┐
    │           Scheduler Factory               │
    ├──────────┬──────────┬──────────┬─────────┤
    │  Hybrid  │   EDF    │ Priority │  Round  │
    │(AI+aging)│(deadline)│ (static) │  Robin  │
    └──────────┴──────────┴──────────┴─────────┘
         │
    ┌────▼───────────────────────────────────────┐
    │              AI Advisor                     │
    │  RandomForest → fault probability →         │
    │  graduated priority boost (0–12 pts)        │
    └─────────────────────────────────────────────┘
         │
    ┌────▼───────────────────────────────────────┐
    │              Metrics Engine                 │
    │  10+ KPIs: deadline miss rate, CPU util,    │
    │  throughput, turnaround, fault breakdown... │
    └─────────────────────────────────────────────┘
```

---

## Benchmark Results

All four schedulers run on an identical workload (seed=42, 200 steps):

| Metric                  | Hybrid (AI) | EDF       | **Priority** | Round Robin |
|-------------------------|-------------|-----------|--------------|-------------|
| Completion Rate         | 95.8%       | 93.2%     | **97.8%**    | 100.0% ★    |
| **Deadline Miss Rate**  | 100%        | 80.5%     | **11.1% ★**  | 90.9%       |
| CPU Utilization         | 100%        | 100%      | 100%         | 100%        |
| Throughput (tasks/step) | 0.115       | 0.205     | **0.225 ★**  | 0.110       |
| Avg Turnaround (ticks)  | 101.0       | 72.7      | **15.8 ★**   | 87.6        |
| Total Faults            | 175         | 184       | **48 ★**     | 171         |
| Context Switches        | 200         | **47 ★**  | 62           | 200         |
| Energy Consumed         | 235.9       | **227.7** | 231.1 ★      | 237.0       |
| AI Interventions        | 200         | 200       | 200          | 200         |

**Key insight:** Static Priority dominates on deadline miss rate (11.1% vs 80–100%) because critical sensor tasks are statically promoted above housekeeping tasks. EDF yields the fewest context switches. Round Robin achieves 100% completion but at the cost of 90.9% deadline misses.

Reproduce with:
```bash
python scripts/compare_schedulers.py --seed 42 --steps 200
```

---

## Key Features

### 1. Four Scheduling Algorithms
| Algorithm | Strategy | Best For |
|-----------|----------|----------|
| **Hybrid** | Multi-factor weighted score: criticality + priority + aging + AI boost − execution penalty | General workloads with mixed task types |
| **EDF** | Earliest Deadline First | Hard real-time with known deadlines |
| **Priority** | Static priority with critical-task promotion | Mission-critical with stable priority hierarchy |
| **Round Robin** | Equal time quantum (fairness baseline) | Throughput benchmarking |

### 2. Physics-Informed Fault Model
Faults are driven by **system state**, not bare dice rolls:

```
fault_probability = base_task_risk
                  × memory_pressure_multiplier   (1.0 → 3.5×)
                  × deadline_urgency_factor       (1.0 → 4.0×)
                  × critical_task_factor          (1.0 or 1.2×)
```

This means the AI advisor learns real correlations between memory pressure, deadline proximity, and fault likelihood — not statistical noise.

### 3. Priority Inheritance Protocol (PIP)

Demonstrates and solves the [Mars Pathfinder 1997 priority inversion bug](https://www.cs.cornell.edu/courses/cs6410/2010fa/lectures/09-mars-pathfinder.pdf):

```
Scenario:
  LOW  (priority 1)  holds "sensor_bus" lock
  HIGH (priority 9)  blocks on "sensor_bus"
  MED  (priority 5)  ready to run

Without PIP:  MED preempts LOW → HIGH starves  ← PRIORITY INVERSION
With PIP:     LOW inherits priority 9 → MED cannot preempt → HIGH runs on time
```

Verified by a deterministic test suite:
```bash
pytest tests/test_priority_inversion.py -v
```

### 4. AI Fault Advisor
- **Model:** Random Forest trained on AUV telemetry (task type, memory pressure, deadline proximity)
- **Output:** Graduated priority boost (0, 1, 4, 8, or 12 points) based on fault probability
- **Precision:** 79% of AI interventions preceded an actual fault (seed=42)
- **Design decision:** Inference-only at runtime; model is trained offline on historical simulation data. This mirrors production ML deployment where retraining during operation is unacceptable.

### 5. Comprehensive Metrics Engine
10+ KPIs tracked per simulation run, exportable to JSON:
- `deadline_miss_rate`, `task_completion_rate`, `throughput`
- `cpu_utilization`, `average_waiting_time`, `average_turnaround_time`
- `context_switches`, `fault_rate`, `fault_breakdown` (by type)
- `energy_consumed`, `ai_interventions`, `ai_precision`

---

## Quick Start

```bash
# Setup
git clone https://github.com/shubhthakkar06/SentinelOS
cd SentinelOS
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run with default hybrid scheduler
python -m sentinel_os

# Run a specific scheduler with Gantt chart
python -m sentinel_os --scheduler edf --seed 42 --gantt

# Benchmark all schedulers
python scripts/compare_schedulers.py --seed 42 --steps 300

# Run the test suite
pytest tests/ -v
```

---

## Requirements

```
matplotlib>=3.7
pandas>=2.0
scikit-learn>=1.3
pyyaml>=6.0
pytest>=7.0
```

---

## Design Decisions

**Why Random Forest, not a neural network?**
Inference latency for the scheduler must be sub-millisecond. Random Forest provides deterministic, bounded inference time unlike deep networks. The feature space is small enough (7 features) that tree ensembles are statistically optimal.

**Why a microkernel architecture?**
AUV fault isolation: if the DataLogging service crashes, Navigation continues. A monolithic design would require rebooting the entire system — not possible at depth.

**Why PIP over Priority Ceiling Protocol (PCP)?**
PIP requires no upfront declaration of maximum priority usage, which suits AUV missions where task graphs change at runtime (e.g., obstacle detected → new task spawned at high priority).

---

## Test Suite

53 deterministic tests across 4 modules:

```
tests/
├── test_scheduler.py           # EDF, Priority, RR, Hybrid correctness
├── test_priority_inversion.py  # PIP demonstration + verification
├── test_metrics.py             # KPI calculation accuracy
└── test_resource_manager.py    # Memory allocation & energy tracking
```

```bash
pytest tests/ -v
# 53 passed in 0.04s
```

---

## Project Structure

```
SentinelOS/
├── sentinel_os/
│   ├── __main__.py              # CLI entry point
│   ├── core/
│   │   ├── task.py              # Task state machine + fault model
│   │   ├── kernel.py            # Kernel + scheduler dispatch
│   │   ├── system_simulator.py  # Main simulation loop
│   │   └── context_switch.py
│   ├── scheduler/
│   │   ├── algorithms/
│   │   │   ├── hybrid.py        # AI-advised weighted scheduler
│   │   │   ├── edf.py           # Earliest Deadline First
│   │   │   ├── priority.py      # Static Priority
│   │   │   └── round_robin.py   # Round Robin
│   │   └── scheduler_factory.py
│   ├── components/
│   │   ├── resource_manager.py  # Memory + energy (with pressure levels)
│   │   ├── lock_manager.py      # Priority Inheritance Mutex
│   │   ├── fault_injector.py    # Fault event injection
│   │   ├── event_manager.py     # IO/Timer events
│   │   └── task_generator.py    # AUV task generation
│   ├── monitoring/
│   │   ├── metrics.py           # 10+ KPI engine
│   │   ├── logger.py            # Structured logging with levels
│   │   ├── visualizer.py        # Gantt chart + comparison plots
│   │   └── dataset_generator.py # ML training data export
│   └── ai/
│       └── ai_advisor.py        # RandomForest fault predictor
├── scripts/
│   └── compare_schedulers.py    # Benchmark CLI
├── tests/                       # 53 pytest tests
└── data/                        # Generated training datasets
```
