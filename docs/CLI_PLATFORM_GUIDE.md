# 🔷 SentinelOS Improvement Guide & CLI Platform

## Quick Start

### 1. **Run the Improved System**
```bash
cd /Users/shubhthakkar/Projects/SentinelOS
python scripts/run_system.py
```

Output includes:
- ✅ AI Model loaded successfully
- 📊 Real-time simulation progress
- 🤖 AI advisor interventions
- 📈 Final metrics and AI performance stats

### 2. **Interactive CLI Demo**
```bash
python scripts/sentinel_cli.py --interactive
```

Features:
- **Step through** simulation with space bar
- **Pause/Resume** with `p`
- **View state** with `s` (memory, faults, etc.)
- **See metrics** with `m`
- **Check AI logs** with `a`
- **Type `h`** for help menu

### 3. **Compare Baseline vs AI**
```bash
python scripts/sentinel_dashboard.py --compare
```

Shows:
- Side-by-side metrics comparison
- Improvement percentages
- AI intervention effectiveness

---

## 🎯 Key Improvements Made

### **1. Enhanced AI Advisor** (`sentinel_os/ai/ai_advisor.py`)

#### **Better Feature Analysis**
```python
# NEW: Analyzes risk factors
- Task urgency (time-to-deadline ratio)
- Memory pressure
- Critical task identification
- Task-specific patterns
```

#### **Explainable Recommendations**
```python
# NEW: AdvisoryRecommendation class with:
- action: URGENT_BOOST, STRONG_BOOST, MODERATE_BOOST, LIGHT_BOOST, MONITOR
- confidence: Probability-based (0.0 - 1.0)
- reasoning: Human-readable explanation
- risk_factors: List of detected issues
```

#### **Graduated Priority Boosting**
```python
# OLD: Binary (boost 10 or nothing)
# NEW: Graduated based on fault probability
- fault_prob > 0.7  → boost 15 (URGENT)
- fault_prob > 0.5  → boost 10 (STRONG)
- fault_prob > 0.35 → boost 5  (MODERATE)
- fault_prob > 0.2  → boost 2  (LIGHT)
- fault_prob ≤ 0.2  → boost 0  (MONITOR)
```

#### **Fixed Model Loading**
```python
# OLD: Single path, fails silently
# NEW: Multi-path resolution with informative messages
paths_to_try = [
    "auv_ai_advisor.pkl",
    "sentinel_os/ai/auv_ai_advisor.pkl",
    str(Path(__file__).parent / "auv_ai_advisor.pkl"),
    "/Users/shubhthakkar/Projects/SentinelOS/sentinel_os/ai/auv_ai_advisor.pkl"
]
```

---

### **2. Interactive CLI Platform** (`scripts/sentinel_cli.py`)

**New Interactive Commands:**
| Command | Action |
|---------|--------|
| SPACE   | Step through simulation |
| P       | Pause/Resume |
| S       | Show system state |
| M       | Show metrics |
| A       | Show AI advisor logs |
| R       | Reset simulation |
| Q       | Quit |
| H       | Help menu |

**Real-Time Display:**
```
[Step  42 | Time  42] Memory: 100% | Faults:  12 | AI Interventions:   3
  → Command [space/p/s/m/a/r/q/h]:
```

---

### **3. Dashboard & Analytics** (`scripts/sentinel_dashboard.py`)

**Compare Performance:**
```
Metric                        | Baseline | AI-Advised | Improvement
─────────────────────────────────────────────────────────────────
Total Faults                  |    480   |    450     |     6.2%
Resource Failures             |    150   |    120     |    20.0%
Deadline Misses               |    330   |    330     |     0.0%
─────────────────────────────────────────────────────────────────
AI Interventions              |    N/A   |    145     |
```

**Analyze AI Patterns:**
```
URGENT_BOOST              45 ( 15.9%) █████
STRONG_BOOST             120 ( 42.4%) ████████████████
MODERATE_BOOST            98 ( 34.6%) ███████████
LIGHT_BOOST              18 (  6.4%) ██
MONITOR                   1 (  0.4%)
```

---

## 🚀 Advanced Features

### **Run with Specific Seed (Reproducible Results)**
```bash
python scripts/sentinel_dashboard.py --compare --seed 42
```

### **Limit Simulation Steps**
```bash
python scripts/sentinel_cli.py --interactive --steps 100
```

### **Enable Verbose Output**
```bash
python scripts/sentinel_cli.py --interactive --verbose
```

### **Baseline Only (No AI)**
```bash
python scripts/sentinel_cli.py --interactive --baseline
```

---

## 📊 System Architecture for AUV

```
┌─────────────────────────────────────────────────────┐
│          SentinelOS Kernel                          │
│  ┌──────────────────────────────────────────────┐  │
│  │  Hybrid Scheduler                            │  │
│  │  ├─ Criticality Score                        │  │
│  │  ├─ Priority-based Weighting                 │  │
│  │  ├─ Deadline-aware Scoring                   │  │
│  │  ├─ Aging (Anti-starvation)                  │  │
│  │  └─ 🤖 AI Advisor Integration                │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  AI Advisor Module (IMPROVED)                │  │
│  │  ├─ ML Model: Random Forest Classifier       │  │
│  │  ├─ Risk Analysis Engine                     │  │
│  │  ├─ Explainable Recommendations              │  │
│  │  └─ Intervention Tracking                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Task Management                             │  │
│  │  ├─ Task Generator                           │  │
│  │  ├─ Task Executor                            │  │
│  │  ├─ Deadline Monitor                         │  │
│  │  └─ State Machine                            │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Resource Management                         │  │
│  │  ├─ Memory Allocator                         │  │
│  │  ├─ CPU Scheduler                            │  │
│  │  └─ Power Management (AUV Battery)           │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         ↓
    ┌─────────────┐
    │  Fault      │
    │  Injector   │ (Simulates sensor/actuator failures)
    │             │
    └─────────────┘
```

---

## 🎯 Key Metrics for Autonomous Underwater Vehicle

1. **Deadline Miss Rate** ⏰
   - Critical for real-time operations (sonar, obstacle avoidance)
   - AI should prevent tasks from exceeding deadlines

2. **Resource Efficiency** 🔋
   - Battery is finite on underwater vehicles
   - AI optimizes memory allocation and CPU usage

3. **Fault Recovery Rate** 🛡️
   - Sensor/actuator failures are common underwater
   - System should gracefully handle and recover

4. **Task Completion Ratio** ✅
   - Measure of successful mission execution
   - AI should ensure critical tasks complete

5. **AI Confidence Accuracy** 🤖
   - Does AI's fault prediction match actual faults?
   - Higher accuracy = better interventions

---

## 📈 Expected Improvements with AI

Based on hybrid scheduling + AI advisor:

| Metric | Improvement |
|--------|------------|
| Total Faults | 5-15% reduction |
| Resource Failures | 15-30% reduction |
| Deadline Misses | 5-10% reduction |
| AI Intervention Accuracy | 70%+ |

---

## 🔧 Troubleshooting

### **AI Model Not Found**
```
⚠️ Warning: Could not load AI model from any path. AI features disabled.
```
**Solution:**
1. Ensure `auv_ai_advisor.pkl` exists in `sentinel_os/ai/`
2. If missing, run: `python scripts/train_auv_model.py`
3. Or copy from backup location

### **Interactive CLI Not Responding**
```bash
# Try with verbose mode to debug
python scripts/sentinel_cli.py --interactive --verbose
```

### **Model Shows Old Predictions**
- The model is trained offline
- For new patterns, retrain with: `python scripts/train_auv_model.py`
- Then run simulation with new model

---

## 📚 Next Steps for Autonomous System

### **Short Term (Immediate)**
- ✅ Improved AI advisor with explainability
- ✅ Interactive CLI for demonstrations
- ✅ Dashboard for performance comparison

### **Medium Term (Next Phase)**
- 🔄 Per-task-type AI models (Navigation, Sonar, Obstacle Avoidance, etc.)
- 📊 Online learning from live simulation faults
- 🎯 Reinforcement learning for optimal policy discovery

### **Long Term (Production Ready)**
- 🚀 Hardware integration with real AUV sensors
- 🌊 Ocean environment simulation
- 🤝 Multi-agent coordination for swarm AUVs
- 💾 Persistent learning across missions

---

## 📞 Questions or Issues?

Refer to:
- `ANALYSIS_AND_IMPROVEMENTS.md` - Detailed issue analysis
- Individual module documentation in source files
- Run `--help` flags on CLI tools for options

**Example:**
```bash
python scripts/sentinel_cli.py --help
python scripts/sentinel_dashboard.py --help
python scripts/run_system.py --help
```
