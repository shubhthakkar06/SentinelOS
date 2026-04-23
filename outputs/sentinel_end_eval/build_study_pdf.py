from __future__ import annotations

import ast
import json
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path("/Users/shubhthakkar/Projects/SentinelOS")
OUT_DIR = ROOT / "outputs" / "sentinel_end_eval"
PDF_PATH = OUT_DIR / "SentinelOS_End_Evaluation_Study_Guide.pdf"
SLIDE_PREVIEW_DIR = ROOT / "tmp" / "slides" / "sentinel_end_eval" / "preview"


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=30,
        leading=36,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#063447"),
        spaceAfter=18,
    )
)
styles.add(
    ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#073B4C"),
        spaceBefore=8,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="SubTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=colors.HexColor("#0B7285"),
        spaceBefore=8,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12.2,
        textColor=colors.HexColor("#1F2933"),
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334E68"),
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="Tiny",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8.2,
        textColor=colors.HexColor("#334E68"),
    )
)
styles.add(
    ParagraphStyle(
        name="Callout",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        backColor=colors.HexColor("#E6FAFF"),
        borderColor=colors.HexColor("#2CB1BC"),
        borderWidth=0.8,
        borderPadding=6,
        textColor=colors.HexColor("#0A3D4A"),
        spaceBefore=4,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="Question",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9.3,
        leading=12,
        textColor=colors.HexColor("#7C2D12"),
        spaceBefore=6,
        spaceAfter=2,
    )
)
styles.add(
    ParagraphStyle(
        name="CodeBlock",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#102A43"),
    )
)


def p(text: str, style: str = "Body") -> Paragraph:
    safe = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Paragraph(safe, styles[style])


def bullets(items: list[str], level: int = 0) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item, "Body"), leftIndent=12) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=18 + level * 12,
        bulletFontSize=6,
    )


def table(rows, widths=None, font_size=7.4, header=True, repeat=1):
    converted = []
    for row in rows:
        converted.append([cell if hasattr(cell, "wrap") else p(str(cell), "Tiny") for cell in row])
    t = Table(converted, colWidths=widths, repeatRows=repeat if header else 0, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B6D7E2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#073B4C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def code_block(text: str) -> Preformatted:
    return Preformatted(textwrap.dedent(text).strip(), styles["CodeBlock"])


def extract_defs(path: Path) -> str:
    if path.suffix != ".py" or not path.exists():
        return ""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return ""
    parts = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            suffix = f" methods: {', '.join(methods[:10])}" if methods else ""
            if len(methods) > 10:
                suffix += f", +{len(methods) - 10} more"
            parts.append(f"class {node.name}{suffix}")
        elif isinstance(node, ast.FunctionDef):
            parts.append(f"def {node.name}()")
    return "; ".join(parts)


FILE_SUMMARIES = {
    "README.md": "Project overview, architecture diagram, benchmark table, feature list, design decisions, quick start, and test-suite summary. Use it as the official project narrative.",
    "IMPROVEMENTS_ROADMAP.md": "Planning document listing improvements from earlier project state: metrics, config, logging, export, tests, dashboard, AI, and future ideas.",
    "requirements.txt": "Python dependencies: matplotlib, pandas, scikit-learn, pyyaml, and pytest.",
    "conftest.py": "Adds project root to sys.path so tests can import sentinel_os without package installation.",
    "docs/CLI_PLATFORM_GUIDE.md": "Older CLI improvement guide explaining the AI advisor, dashboard, commands, and expected comparisons.",
    "data/auv_task_data.csv": "Generated training/evaluation dataset. Each row records one task sample: time, task type, priority, criticality, memory, depth, recommended priority, and fault flag.",
    "data/experiment_results_chart.png": "Presentation-ready chart from run_experiment.py comparing baseline and adaptive AI on faults.",
    "data/sentinel_dashboard.png": "Generated dashboard image from visualize_demo.py.",
    "results/benchmark_summary.json": "Combined benchmark output for all schedulers. Good source for final results.",
    "results/edf_results.json": "EDF scheduler KPI output.",
    "results/hybrid_results.json": "Hybrid scheduler KPI output.",
    "results/priority_results.json": "Static Priority scheduler KPI output.",
    "results/rr_results.json": "Round Robin scheduler KPI output.",
    "results/scheduler_comparison.png": "Generated scheduler KPI comparison chart.",
    "sentinel_os/__main__.py": "Main CLI entry point for python -m sentinel_os. Parses scheduler, steps, seed, AI flag, exports, charts, comparison mode, and interactive shell.",
    "sentinel_os/core/task.py": "Defines TaskState and Task. This is the core process model: task metadata, resource needs, energy draw, state transitions, I/O waiting, faulting, recovery, execution, and physics-informed fault probability.",
    "sentinel_os/core/system_simulator.py": "Central simulation engine. Owns time loop, environment ticks, event generation, task generation, admission control, scheduling, context switches, execution, resource allocation, AI boosts, fault injection, metrics, survival mode, and operator controls.",
    "sentinel_os/core/kernel.py": "Thin kernel wrapper around scheduler. Applies admission control through ResourceManager, adds tasks, fetches next task, and requeues tasks.",
    "sentinel_os/core/context_switch.py": "Small helper that prints context-switch messages and is used by SystemSimulator when scheduled task changes.",
    "sentinel_os/core/config.py": "Configuration helper with defaults, JSON/YAML loading, SOS_* environment overrides, getters/setters, and save support. Currently not heavily wired into simulator.",
    "sentinel_os/core/shell.py": "Primary rich terminal shell. Implements boot sequence, process commands, scheduler switching, navigation, sensors, comms, BMS, dashboards, blackbox export, survival/emergency modes, and AI command wrappers.",
    "sentinel_os/components/resource_manager.py": "Manages memory pool, admission control, memory pressure, BMS delegation, energy consumption, survival mode transitions, resource snapshots, and stats.",
    "sentinel_os/components/battery.py": "Battery Management System. Models 8 lithium-ion cells, SOC, voltage curve, voltage under load, cell temperature, health degradation, thermal throttling, ETA, and pack stats.",
    "sentinel_os/components/environment.py": "Underwater environment model. Tracks depth, heading, throttle, speed, position, pressure, water temperature, visibility, sonar contacts, comms degradation, hull integrity, ballast, and commands.",
    "sentinel_os/components/task_generator.py": "Creates AUV service and job tasks. Provides core/perception/propulsion/comms/mission groups, priority ranges, burst times, persistent service initialization, and mission/depth-aware task generation.",
    "sentinel_os/components/fault_injector.py": "Injects scenario-aware AUV faults: deadline miss, resource failure, sensor drift, comm lag, seal leak, hull stress, thermal runaway, water ingress, and more.",
    "sentinel_os/components/lock_manager.py": "Implements named mutexes with Priority Inheritance Protocol and deadlock detection. Key file for real-time OS correctness discussion.",
    "sentinel_os/components/event_manager.py": "Simple random event source that generates IO_INTERRUPT or TIMER_INTERRUPT events with 20 percent chance per tick.",
    "sentinel_os/scheduler/scheduler_base.py": "Base interface and shared queues: ready, waiting, blocked, suspended. Defines set_ai_advisor, add_task, get_next_task, requeue, remove_task, and get_queued_tasks contract.",
    "sentinel_os/scheduler/scheduler_factory.py": "Maps policy names to scheduler classes: priority, edf, hybrid, rr.",
    "sentinel_os/scheduler/algorithms/hybrid.py": "AI-advised weighted scheduler. Score combines criticality, effective priority, aging, deadline, cached AI boost, and execution penalty.",
    "sentinel_os/scheduler/algorithms/edf.py": "Earliest Deadline First scheduler. Sorts ready tasks by nearest deadline, then highest effective priority.",
    "sentinel_os/scheduler/algorithms/priority.py": "Static priority scheduler. Critical tasks first, then effective priority, then lower energy usage as tie-break.",
    "sentinel_os/scheduler/algorithms/round_robin.py": "Fairness baseline. Pops ready tasks in FIFO order and requeues unfinished tasks at the back.",
    "sentinel_os/ai/ai_advisor.py": "Loads RandomForest model, constructs feature vectors, predicts fault probability, identifies risk factors, creates AdvisoryRecommendation, and converts probability to priority boost.",
    "sentinel_os/ai/auv_ai_advisor.pkl": "Pickled offline RandomForest model and feature list loaded by AIAdvisor.",
    "sentinel_os/monitoring/metrics.py": "KPI engine. Tracks steps, task lifecycle, deadline misses, CPU utilization, waiting/turnaround, throughput, context switches, faults, energy, AI interventions, JSON export, and summary printing.",
    "sentinel_os/monitoring/logger.py": "Structured logger with log levels, optional stdout, optional file handler, and recent log history. Caveat: optional file output references Path but Path is not imported.",
    "sentinel_os/monitoring/dataset_generator.py": "Appends task samples to data/auv_task_data.csv so the ML model can be trained from simulated telemetry.",
    "sentinel_os/monitoring/visualizer.py": "Matplotlib visualizer for Gantt chart, scheduler comparison chart, and resource-over-time plot.",
    "sentinel_os/shell/commands/advisory_cmd.py": "Rich command for current AI advisory table across tasks: risk, confidence, boost, and action.",
    "sentinel_os/shell/commands/predict_cmd.py": "Rich command focused on Module 1 fault prediction display.",
    "sentinel_os/shell/commands/prioritize_cmd.py": "Rich command focused on Module 2 resource/priority recommendation display.",
    "sentinel_os/shell/commands/compare_cmd.py": "Rich benchmark table command. Caveat: numbers are hard-coded/readme-derived and should be synced with current results.",
    "scripts/compare_schedulers.py": "Benchmark runner for Hybrid, EDF, Priority, and Round Robin with same seed and steps. Writes per-scheduler JSON, combined JSON, and optional comparison chart.",
    "scripts/run_system.py": "Simple one-shot simulation runner with AI enabled and terminal summary.",
    "scripts/run_experiment.py": "Runs baseline vs adaptive AI experiment, prints comparison, and saves data/experiment_results_chart.png.",
    "scripts/sentinel_cli.py": "Older interactive cmd.Cmd demo shell. Some references appear stale compared with current SystemSimulator, so use primary python -m sentinel_os shell for final demo.",
    "scripts/sentinel_dashboard.py": "Dashboard/analytics script for baseline-vs-AI comparison and AI recommendation distribution analysis. Some simplified code paths are older.",
    "scripts/train_auv_model.py": "Notebook-style script that loads data/auv_task_data.csv, one-hot encodes task_type, trains RandomForest, evaluates, and saves a model pickle.",
    "scripts/AUV_model_RF.ipynb": "Notebook version of the RandomForest training workflow.",
    "scripts/visualize_demo.py": "Creates a dark Matplotlib dashboard from data/auv_task_data.csv with memory line plot and fault scatter.",
    "tests/test_scheduler.py": "Deterministic tests for EDF, Priority, Round Robin, and Hybrid scheduler behavior.",
    "tests/test_priority_inversion.py": "Tests for PIP: inversion detection, boost, priority restoration, lock transfer, full scenario, and deadlock checks.",
    "tests/test_metrics.py": "Tests KPI calculations. Current failures show tests expect older AI precision API.",
    "tests/test_resource_manager.py": "Tests memory, pressure, and legacy energy behavior. Current energy tests expect old flat battery model, so BMS refactor makes some fail.",
}


ARCH_FLOW = """
1. User starts: python -m sentinel_os --scheduler priority --seed 42 --steps 200
2. __main__.py parses arguments and creates SystemSimulator.
3. SystemSimulator initializes:
   AIAdvisor, ResourceManager+BMS, Kernel+Scheduler, TaskGenerator,
   FaultInjector, EventManager, LockManager, UnderwaterEnvironment,
   Metrics, Logger, DatasetGenerator, ContextSwitch.
4. initialize() creates persistent AUV services and admits them into the scheduler.
5. Each step:
   environment.tick()
   event_manager.generate_events()
   task_generator.generate_task()
   kernel.add_tasks() with admission control
   waiting I/O tasks tick back toward READY
   scheduler selects next READY task
   context switch is recorded
   resource_manager.allocate(task)
   task.execute(time_slice=2, system_state)
   resource_manager.consume_energy(task)
   AIAdvisor may boost task.effective_priority
   FaultInjector injects faults
   Metrics and DatasetGenerator record outcomes
   task recovers, completes, blocks, waits, or requeues
6. End: metrics.to_dict() returns KPIs, optional JSON/plots are exported.
"""


SLIDE_EXPLANATIONS = [
    ("1. SentinelOS", "Start with identity: this is an AI-advised microkernel OS simulator for AUVs. Mention it is a simulator, not real hardware. Explain the four project pillars: real-time scheduling, fault prediction, priority inheritance, and benchmarking."),
    ("2. Background", "Explain why AUVs are a good domain: no reboot at depth, finite battery, pressure/temperature risk, and hard deadlines for navigation/sonar/depth control."),
    ("3. Problem Statement", "Say the goal is to protect mission-critical AUV processes by predicting faults, adapting priority safely, modeling constraints, and benchmarking scheduler policies."),
    ("4. Mid to Final", "Show progress from proposal to implementation. Mid-eval had planned modules; final has code for task lifecycle, schedulers, resources, environment, BMS, shell, AI advisor, tests, and metrics."),
    ("5. Architecture", "Walk layer by layer: simulator drives time, kernel delegates scheduling, resource layer manages memory/BMS, adaptive layer gives AI advice, monitoring layer records metrics and outputs."),
    ("6. Task Model", "Explain process states. Important: WAITING is I/O wait, BLOCKED is resource/lock wait, FAULT is recoverable fault state, SUSPENDED is operator/kernel pause. Persistent services respawn."),
    ("7. Scheduling", "Compare four schedulers. Hybrid is weighted and AI-aware. EDF optimizes deadlines. Static Priority protects critical tasks. RR is fairness baseline."),
    ("8. AI Advisor", "Explain AI is not the scheduler. It predicts risk using RandomForest and returns a boost. Kernel stays deterministic. Features include priority, critical flag, remaining time, memory, and task type."),
    ("9. Fault Model", "Explain fault probability formula. It is physics-informed: base task risk multiplied by memory pressure, deadline urgency, criticality, depth, temperature, and mission mode."),
    ("10. Resources", "Explain memory admission, BMS battery, environment physics, and survival mode. This proves project is domain-aware, not a generic CPU queue toy."),
    ("11. PIP", "Use classic priority inversion story: low holds lock, high waits, medium preempts low. PIP boosts low temporarily so high can proceed. This is a strong OS-theory point."),
    ("12. CLI Demo", "Show how you demonstrate the system: boot shell, top/ps, run/step, scheduler change, mission survival, battery, sonar, benchmark command."),
    ("13. Evaluation", "Explain seeded benchmark: same workload, AI enabled, 200 steps. Static Priority wins completion, deadline miss, and total faults in this run. EDF wins context switches; RR wins energy."),
    ("14. Validation", "Be honest: 53 tests written, 48 currently pass. Five failures are from old tests expecting pre-BMS/old AI precision API. Present this as known integration debt after refactor."),
    ("15. Conclusion", "Summarize: implemented OS concepts plus AUV constraints plus AI advisory. Main learning: deterministic kernel control can use ML as an advisor without giving ML unsafe authority."),
]


VIVA_QA = [
    ("Why microkernel?", "Because AUV subsystems should be isolated. If DataLogging or comms fails, Navigation/DepthControl should continue. Microkernel thinking separates services and keeps faults contained."),
    ("Is this a real OS?", "No. It is an OS simulator that models OS concepts: process states, scheduling, resource management, interrupts/events, locks, priority inversion, metrics, and shell commands."),
    ("Why Random Forest instead of neural network?", "Small feature space, fast inference, deterministic bounded runtime, easier explanation, and suitable for offline embedded-style deployment."),
    ("Does AI control the kernel?", "No. AIAdvisor only returns an advisory priority boost. Schedulers and kernel still use deterministic rules and effective_priority."),
    ("What is effective_priority?", "It is the runtime priority used by schedulers. It starts from base_priority but may be changed by AI boost or PIP boost."),
    ("What is priority inversion?", "A high-priority task waits for a lock held by a low-priority task, while a medium-priority task preempts the low task. High indirectly starves."),
    ("How does PIP fix it?", "The low-priority lock holder temporarily inherits the high-priority waiter's priority, finishes the critical section, releases the lock, then priority is restored."),
    ("Why do you have both FaultInjector and Task.execute fault probability?", "Task.execute models task-local probabilistic faults from physical/system state. FaultInjector adds explicit scenario-aware events such as deadline misses, comm lag, seal leak, and thermal runaway."),
    ("What is the most important metric?", "Deadline miss rate for real-time systems, plus task completion rate and total faults. Energy and context switches are also important trade-offs."),
    ("Why did Static Priority win the benchmark?", "Critical AUV services have high priority and are promoted, so they finish earlier and miss fewer deadlines on this workload."),
    ("Why does Round Robin have low energy in the shown run?", "It rotates tasks fairly and, in that seeded run, consumed fewer energy units. But it had worse deadline behavior than Static Priority."),
    ("What is admission control?", "ResourceManager rejects transient jobs when job count is too high or memory would dip into reserved service memory. Core services are always admitted."),
    ("What is survival mode?", "When mission mode is Survival and battery drops through phases, the OS suspends non-critical tasks, throttles power, changes sonar behavior, and eventually auto-surfaces."),
    ("What are persistent services?", "Long-lived AUV services like Navigation, DepthControl, HullIntegrity, BatteryMonitor, O2Scrubber, and ThermalRegulation. They reset/respawn instead of disappearing."),
    ("What is the current test status?", "53 tests exist. Current run: 48 pass, 5 fail. Failures are not random: two expect old Metrics.record_ai_intervention signature/ai_precision property, three expect old flat battery drain semantics after BMS refactor."),
    ("What bugs or caveats should you admit?", "logger.py optional file logging needs Path import. compare_cmd.py uses hard-coded old benchmark numbers. sentinel_cli.py is older and may be stale. train_auv_model.py saves to root filename while AIAdvisor usually loads sentinel_os/ai/auv_ai_advisor.pkl."),
]


def benchmark_table_rows():
    path = ROOT / "tmp" / "slides" / "sentinel_end_eval" / "bench" / "benchmark_summary.json"
    if not path.exists():
        path = ROOT / "results" / "benchmark_summary.json"
    data = json.loads(path.read_text())
    rows = [["Scheduler", "Completion", "Deadline Miss", "Faults", "Context Switches", "Energy", "Throughput"]]
    for r in data:
        rows.append(
            [
                r["scheduler"],
                f"{r['task_completion_rate'] * 100:.1f}%",
                f"{r['deadline_miss_rate'] * 100:.1f}%",
                str(r["total_faults"]),
                str(r["context_switches"]),
                f"{r['energy_consumed']:.1f}",
                f"{r['throughput']:.3f}",
            ]
        )
    return rows


def add_cover(story):
    story.append(Spacer(1, 1.2 * inch))
    story.append(p("SentinelOS End Evaluation Study Guide", "CoverTitle"))
    story.append(p("Full project explanation, code walkthrough, PPT speaking script, and viva Q&A", "SubTitle"))
    story.append(Spacer(1, 0.25 * inch))
    story.append(
        p(
            "Use this PDF as your preparation document. It explains what each file does, how the modules connect, how to present every slide, and what questions you should be ready to answer.",
            "Callout",
        )
    )
    story.append(Spacer(1, 0.25 * inch))
    story.append(p("Project: AI-Advised Microkernel Operating System Simulator for Autonomous Underwater Vehicles", "Body"))
    story.append(p("Generated from the local SentinelOS implementation and the end-evaluation PPT.", "Body"))
    story.append(PageBreak())


def add_toc(story):
    story.append(p("How To Use This Guide", "SectionTitle"))
    story.append(
        bullets(
            [
                "First read Sections 1-3 to understand the system in plain language.",
                "Then read the slide-by-slide section and practice the speaking script aloud.",
                "Use the file-by-file section when someone asks where a feature is implemented.",
                "Use the viva section for quick answers before evaluation.",
                "Do not hide known limitations. Explaining them clearly makes you look more prepared.",
            ]
        )
    )
    story.append(p("Table of Contents", "SectionTitle"))
    rows = [
        ["1", "Project in one page"],
        ["2", "System execution flow"],
        ["3", "Core OS concepts mapped to SentinelOS"],
        ["4", "PPT slide-by-slide speaking guide"],
        ["5", "Module-by-module deep dive"],
        ["6", "Every file in the repository"],
        ["7", "Benchmark and test interpretation"],
        ["8", "Likely viva questions and answers"],
        ["9", "Known limitations and honest improvement plan"],
    ]
    story.append(table(rows, widths=[0.4 * inch, 5.8 * inch], header=False, repeat=0))
    story.append(PageBreak())


def add_project_summary(story):
    story.append(p("1. Project In One Page", "SectionTitle"))
    story.append(
        p(
            "SentinelOS is a Python simulator of an AI-advised microkernel-style operating system for Autonomous Underwater Vehicles (AUVs). It is designed to demonstrate real OS concepts in a mission-critical domain: scheduling, process states, resource management, fault handling, locks, priority inversion, metrics, and command-line system monitoring.",
            "Body",
        )
    )
    story.append(
        p(
            "The key design principle is: AI advises, but the deterministic kernel decides. The RandomForest model predicts fault risk and recommends a priority boost. The scheduler still makes the final dispatch decision using explicit rules.",
            "Callout",
        )
    )
    story.append(p("Main implemented capabilities", "SubTitle"))
    story.append(
        bullets(
            [
                "Four schedulers: Hybrid, Earliest Deadline First, Static Priority, and Round Robin.",
                "AUV-specific task model with 15 subsystem task types and persistent core services.",
                "Full process state model: NEW, READY, RUNNING, BLOCKED, WAITING, SUSPENDED, FAULT, TERMINATED.",
                "Physics-informed fault risk using memory pressure, deadline urgency, criticality, depth, battery temperature, and mission mode.",
                "Battery Management System with 8 cells, SOC, voltage sag, temperature, health, ETA, and thermal throttling.",
                "Underwater environment model with depth, pressure, water temperature, comms degradation, sonar contacts, ballast, speed, and hull integrity.",
                "Priority Inheritance Protocol for priority inversion.",
                "Metrics engine, JSON exports, visual charts, rich interactive shell, and deterministic tests.",
            ]
        )
    )
    story.append(p("Fresh benchmark used in final PPT", "SubTitle"))
    story.append(table(benchmark_table_rows(), widths=[0.8 * inch, 0.85 * inch, 1.0 * inch, 0.65 * inch, 0.95 * inch, 0.75 * inch, 0.8 * inch]))
    story.append(PageBreak())


def add_flow(story):
    story.append(p("2. System Execution Flow", "SectionTitle"))
    story.append(p("If an evaluator asks 'what happens when the program runs?', answer with this flow.", "Body"))
    story.append(code_block(ARCH_FLOW))
    story.append(p("Most important mental model", "SubTitle"))
    story.append(
        bullets(
            [
                "SystemSimulator is the conductor. It owns time and calls every subsystem each tick.",
                "Kernel is the admission and scheduling wrapper. It does not contain the scheduling algorithm itself.",
                "Scheduler algorithms only select from READY queue; WAITING, BLOCKED, and SUSPENDED are not runnable.",
                "ResourceManager protects finite memory and energy. It can reject jobs before they enter scheduling.",
                "AIAdvisor calculates a boost but never directly runs or kills a task.",
                "Metrics records enough data to compare schedulers after the run.",
            ]
        )
    )
    story.append(p("One tick, in explainable words", "SubTitle"))
    story.append(
        bullets(
            [
                "Update water/vehicle environment.",
                "Check battery and survival phase.",
                "Generate interrupts/events.",
                "Generate new AUV tasks depending on depth and mission state.",
                "Admit or reject tasks based on memory and job limits.",
                "Move completed I/O wait tasks back to READY.",
                "Scheduler chooses one READY task.",
                "Allocate memory, run task, drain energy, ask AI for priority boost, inject faults.",
                "Record metrics and dataset samples.",
                "Recover, complete, terminate, wait, block, or requeue the task.",
            ]
        )
    )
    story.append(PageBreak())


def add_os_concepts(story):
    story.append(p("3. Core OS Concepts In SentinelOS", "SectionTitle"))
    rows = [
        ["OS concept", "Where in code", "How to explain"],
        ["Process Control Block", "Task object", "Task stores id, type, priority, deadline, critical flag, memory, energy, state, lock info, I/O info, fault history, and runtime stats."],
        ["Process states", "TaskState enum", "A realistic state machine separates READY/RUNNING from BLOCKED, WAITING, SUSPENDED, FAULT, and TERMINATED."],
        ["Scheduler", "scheduler/algorithms/*.py", "Schedulers choose one READY task. They do not execute tasks themselves."],
        ["Kernel", "core/kernel.py", "Kernel adds tasks, applies admission control, delegates dispatch to scheduler, and requeues task states."],
        ["Interrupts/events", "components/event_manager.py", "Random IO_INTERRUPT and TIMER_INTERRUPT events simulate asynchronous OS events."],
        ["Context switch", "core/context_switch.py + metrics", "When selected task changes, context switch is logged and counted."],
        ["Resource management", "components/resource_manager.py", "Memory allocation, energy use, admission control, pressure levels, and survival mode."],
        ["Fault handling", "Task.fault/try_recover + FaultInjector", "Tasks can fault and recover; external fault injector adds AUV-specific failures."],
        ["Priority inversion", "components/lock_manager.py", "PIP boosts lock holder priority to avoid high-priority starvation."],
        ["Monitoring", "monitoring/metrics.py", "KPIs measure correctness and performance: deadlines, throughput, utilization, faults, energy, switches."],
        ["Shell", "core/shell.py", "Operator-style interface to inspect and control the simulated OS."],
    ]
    story.append(table(rows, widths=[1.2 * inch, 1.6 * inch, 3.5 * inch]))
    story.append(PageBreak())


def add_slide_guide(story):
    story.append(p("4. PPT Slide-By-Slide Speaking Guide", "SectionTitle"))
    story.append(
        p(
            "For each slide, read the title, then explain the bullets in your own words. Do not recite paragraphs. The deck is designed so each point opens a topic.",
            "Callout",
        )
    )
    for idx, (title, explanation) in enumerate(SLIDE_EXPLANATIONS, start=1):
        parts = [p(title, "SubTitle")]
        preview = SLIDE_PREVIEW_DIR / f"slide-{idx:02d}.png"
        if preview.exists():
            img = Image(str(preview), width=3.4 * inch, height=1.91 * inch)
            parts.append(img)
        parts.append(p(explanation, "Body"))
        parts.append(
            p(
                "Possible follow-up: connect this slide to the exact files: SystemSimulator, Task, schedulers, ResourceManager, AIAdvisor, FaultInjector, LockManager, Metrics, or Shell depending on topic.",
                "Small",
            )
        )
        story.append(KeepTogether(parts))
        story.append(Spacer(1, 0.12 * inch))
    story.append(PageBreak())


def add_deep_dive(story):
    story.append(p("5. Module-By-Module Deep Dive", "SectionTitle"))
    modules = [
        (
            "Core module",
            [
                "Task is the simulated process. It stores state, priority, deadline, memory, energy, I/O wait, locks, faults, and execution counters.",
                "SystemSimulator is the main loop. It connects every component and is the best file to explain full behavior.",
                "Kernel is intentionally thin. This helps preserve the microkernel-style separation of concerns.",
                "Shell is the user-facing terminal and makes the OS feel alive: boot, ps/top, battery, sonar, mission, scheduler switching, emergency, blackbox.",
            ],
        ),
        (
            "Scheduler module",
            [
                "All schedulers inherit the same queue model from SchedulerBase.",
                "Hybrid computes a weighted score. Criticality and AI boost help urgent/high-risk tasks; aging prevents starvation; execution penalty avoids one task dominating.",
                "EDF optimizes deadlines by selecting the nearest deadline first.",
                "Priority scheduler protects critical services and uses effective_priority, so AI/PIP boosts matter.",
                "Round Robin is the baseline for fairness, useful for comparing trade-offs.",
            ],
        ),
        (
            "Component module",
            [
                "ResourceManager handles admission control and memory. It reserves memory for core services.",
                "BatteryManagementSystem models cells, SOC, voltage, temperature, health, thermal throttle, and ETA.",
                "Environment models the underwater world: depth, pressure, temperature, comms, sonar, hull, ballast, and movement.",
                "TaskGenerator creates realistic AUV tasks based on depth and survival phase.",
                "FaultInjector injects AUV-specific faults based on deadlines, mode, depth, temperature, and task type.",
                "LockManager implements Priority Inheritance Protocol.",
            ],
        ),
        (
            "AI and monitoring",
            [
                "AIAdvisor loads a pickle model, creates feature vectors, predicts fault probability, records reasoning, and converts probability to boost.",
                "Metrics turns raw events into KPIs.",
                "DatasetGenerator writes training samples.",
                "Visualizer creates charts for Gantt, scheduler comparison, and resources.",
                "Logger stores readable event history for shell dashboards.",
            ],
        ),
    ]
    for heading, items in modules:
        story.append(p(heading, "SubTitle"))
        story.append(bullets(items))
    story.append(p("Important formulas and rules", "SubTitle"))
    story.append(
        code_block(
            """
            Task fault probability:
            base_task_risk
              x memory_pressure
              x deadline_urgency
              x critical_factor
              x depth_factor
              x battery_temperature_factor
              x mission_mode_factor

            Hybrid score:
            critical_score + priority_score + aging_score + deadline_score
              + ai_boost_score - execution_penalty

            AI priority boost:
            boost = int(fault_probability * 15)
            effective_priority = base_priority + boost

            PIP:
            if high-priority waiter blocks on lock held by low-priority holder:
                holder.effective_priority = waiter.effective_priority
            """
        )
    )
    story.append(PageBreak())


def file_rows():
    rows = [["File", "What it does", "Main definitions"]]
    files = []
    for rel in FILE_SUMMARIES:
        files.append(ROOT / rel)
    for file_path in files:
        rel = file_path.relative_to(ROOT).as_posix()
        rows.append([rel, FILE_SUMMARIES[rel], extract_defs(file_path)])
    return rows


def add_file_walkthrough(story):
    story.append(p("6. Every File In The Repository", "SectionTitle"))
    story.append(
        p(
            "Generated cache folders such as __pycache__, venv, tmp, and outputs are not source code and are intentionally excluded. The table below covers the project files you may be asked about.",
            "Callout",
        )
    )
    rows = file_rows()
    story.append(table(rows, widths=[1.65 * inch, 3.1 * inch, 1.7 * inch], font_size=6.7))
    story.append(PageBreak())


def add_results_and_tests(story):
    story.append(p("7. Benchmark And Test Interpretation", "SectionTitle"))
    story.append(p("Benchmark command used for the final deck", "SubTitle"))
    story.append(code_block("venv/bin/python scripts/compare_schedulers.py --seed 42 --steps 200 --output tmp/slides/sentinel_end_eval/bench --no-chart"))
    story.append(table(benchmark_table_rows(), widths=[0.8 * inch, 0.85 * inch, 1.0 * inch, 0.65 * inch, 0.95 * inch, 0.75 * inch, 0.8 * inch]))
    story.append(p("How to explain the results", "SubTitle"))
    story.append(
        bullets(
            [
                "Static Priority is best for this workload because critical AUV services are promoted and deadline-sensitive work finishes earlier.",
                "EDF has the fewest context switches, which can be good for overhead, but in this run it missed more deadlines due to workload/service behavior.",
                "Round Robin is fair and had lowest energy in this seed, but deadline behavior is weaker because it ignores urgency.",
                "Hybrid uses AI and aging, but tuning matters. AI advice is useful, but it does not guarantee best results on every metric.",
            ]
        )
    )
    story.append(p("Current test status", "SubTitle"))
    story.append(
        p(
            "Command run: venv/bin/python -m pytest -q. Result: 48 passed, 5 failed out of 53. The failures are explainable integration debt, not random unknown behavior.",
            "Callout",
        )
    )
    rows = [
        ["Failing area", "Reason", "How to answer"],
        ["Metrics AI precision tests", "Tests call record_ai_intervention(predicted_fault=..., actual_fault=...), but current Metrics uses outcome strings such as PREVENTION_SUCCESS and ACCURATE_PREDICTION.", "Say the metrics API changed during AI intervention refactor; tests need updating or backward compatibility wrapper."],
        ["ResourceManager battery tests", "Tests expect simple flat current_battery drain by exact task.energy_usage. Current implementation delegates to realistic BMS, so SOC decreases non-linearly and not by direct subtraction.", "Say BMS refactor improved realism, but old tests still assert legacy battery semantics."],
    ]
    story.append(table(rows, widths=[1.5 * inch, 2.6 * inch, 2.3 * inch]))
    story.append(PageBreak())


def add_viva(story):
    story.append(p("8. Likely Viva Questions And Answers", "SectionTitle"))
    for question, answer in VIVA_QA:
        story.append(p("Q: " + question, "Question"))
        story.append(p("A: " + answer, "Body"))
    story.append(PageBreak())


def add_limitations(story):
    story.append(p("9. Known Limitations And Improvement Plan", "SectionTitle"))
    story.append(p("Say these confidently if asked. Honest limitations are better than pretending everything is production-ready.", "Callout"))
    rows = [
        ["Limitation", "Why it matters", "Fix"],
        ["Simulator, not real hardware", "No certified real-time guarantees or hardware drivers.", "Keep scope clear; future work can integrate real RTOS/hardware-in-loop."],
        ["AI model pickle version warning", "Model trained with older scikit-learn than current runtime.", "Regenerate auv_ai_advisor.pkl with current environment and save under sentinel_os/ai/."],
        ["Some scripts are older", "sentinel_cli.py and compare_cmd.py have stale assumptions/hard-coded numbers.", "Use python -m sentinel_os primary shell and scripts/compare_schedulers.py for evaluation."],
        ["Tests need refactor sync", "5 tests assume old metric and battery behavior.", "Update tests for outcome-based AI metrics and BMS semantics."],
        ["Logger optional file bug", "Path is referenced without import if log_file is used.", "Add from pathlib import Path in logger.py."],
        ["Single-run benchmark", "One seed does not prove statistical superiority.", "Run multiple seeds and report mean/std/confidence intervals."],
        ["No persistent database", "JSON outputs are useful but not queryable across long experiments.", "Add SQLite or pandas analysis pipeline."],
    ]
    story.append(table(rows, widths=[1.55 * inch, 2.4 * inch, 2.45 * inch]))
    story.append(p("Final 60-second summary to memorize", "SubTitle"))
    story.append(
        p(
            "SentinelOS is a Python OS simulator for AUVs. It models AUV tasks as processes, schedules them with four policies, tracks memory and battery through a ResourceManager and BMS, simulates underwater environment and faults, uses a RandomForest AI advisor to predict fault risk and boost priority, implements Priority Inheritance Protocol to solve priority inversion, and evaluates everything with KPIs and tests. The main safety design is that AI only advises; deterministic schedulers and kernel logic remain in control.",
            "Callout",
        )
    )


def add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#607D8B"))
    canvas.drawString(0.6 * inch, 0.35 * inch, "SentinelOS End Evaluation Study Guide")
    canvas.drawRightString(A4[0] - 0.6 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="SentinelOS End Evaluation Study Guide",
        author="Codex",
    )
    story = []
    add_cover(story)
    add_toc(story)
    add_project_summary(story)
    add_flow(story)
    add_os_concepts(story)
    add_slide_guide(story)
    add_deep_dive(story)
    add_file_walkthrough(story)
    add_results_and_tests(story)
    add_viva(story)
    add_limitations(story)
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return PDF_PATH


if __name__ == "__main__":
    print(build_pdf())
