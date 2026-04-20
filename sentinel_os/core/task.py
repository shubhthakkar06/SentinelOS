"""
sentinel_os/core/task.py
-------------------------
Proper process model for SentinelOS.

Implements a real OS process state machine:

    NEW ──► READY ──► RUNNING ──► TERMINATED (success)
                         │
                         ├──► BLOCKED  (waiting on resource/lock)
                         │       └──► READY   (resource freed)
                         │
                         └──► FAULT    (hardware/software fault)
                                 ├──► READY   (recovered)
                                 └──► TERMINATED (unrecoverable)

Key improvement over the original:
  - Faults are driven by SYSTEM STATE (memory pressure, deadline proximity)
    rather than bare random.random() dice rolls.
  - A physics-informed fault model makes the AI advisor's training data
    genuinely meaningful — it learns correlations between system state
    and fault outcomes.
"""

import random
from enum import Enum


class TaskState(str, Enum):
    NEW        = "NEW"
    READY      = "READY"
    RUNNING    = "RUNNING"
    BLOCKED    = "BLOCKED"     # waiting on resource / lock
    FAULT      = "FAULT"       # transient hardware/software fault
    TERMINATED = "TERMINATED"  # completed or permanently failed


# AUV task types with inherent risk profiles
TASK_TYPE_RISK: dict = {
    "Navigation":        0.03,   # low risk, well-tested paths
    "ObstacleAvoidance": 0.08,   # sensor-dependent, higher risk
    "SonarPing":         0.05,   # I/O bound, moderate risk
    "DepthControl":      0.06,   # actuator-dependent
    "BatteryMonitor":    0.02,   # pure computation, low risk
    "DataLogging":       0.03,   # I/O but not time-critical
}

# Memory requirement per task type (units out of 100)
TASK_MEMORY_REQ: dict = {
    "Navigation":        8,
    "ObstacleAvoidance": 12,
    "SonarPing":         5,
    "DepthControl":      6,
    "BatteryMonitor":    3,
    "DataLogging":       4,
}


class Task:
    """
    Represents a single AUV process with a deterministic state machine
    and physics-informed fault probability.
    """

    def __init__(
        self,
        tid: int,
        task_type: str,
        base_priority: int,
        deadline: int | None = None,
        critical: bool = False,
        burst_time: int | None = None,
    ):
        self.tid = tid
        self.task_type = task_type
        self.base_priority = base_priority
        self.deadline = deadline
        self.critical = critical

        # Execution timing
        self.burst_time: int = burst_time if burst_time is not None else random.randint(4, 12)
        self.remaining_time: int = self.burst_time
        self.arrival_time: int = 0       # set by TaskGenerator

        # State machine
        self.state: TaskState = TaskState.NEW
        self.recovery_attempts: int = 0
        self._max_recovery: int = 2      # after this many faults, permanently fail

        # Resource usage
        self.memory_required: int = TASK_MEMORY_REQ.get(task_type, 5)
        self.energy_usage: float = round(random.uniform(0.5, 2.0), 3)

        # Scheduling metadata
        self.waiting_time: int = 0       # accumulated ticks waiting in queue
        self.effective_priority: int = base_priority   # modified by priority inheritance

        # Lock state (for priority inversion demo)
        self.held_lock: str | None = None      # lock name currently held
        self.waiting_for_lock: str | None = None
        
        # Fault Tracking
        self.fault_history: set[str] = set()    # avoids multi-recording the same event
        
        # AI & Diagnostics
        self.ai_boost: int = 0
        self.blocked_reason: str | None = None

    # ------------------------------------------------------------------ #
    #  State transitions                                                   #
    # ------------------------------------------------------------------ #

    def ready(self):
        """Transition to READY (from NEW, BLOCKED, or recovered from FAULT)."""
        self.state = TaskState.READY
        self.blocked_reason = None

    def start_running(self):
        """Transition to RUNNING when the scheduler dispatches this task."""
        assert self.state == TaskState.READY, \
            f"Task {self.tid}: can only run from READY, currently {self.state}"
        self.state = TaskState.RUNNING

    def block(self, reason: str = "RES"):
        """Task is blocked waiting for a resource or lock."""
        self.state = TaskState.BLOCKED
        self.blocked_reason = reason

    def terminate(self):
        """Task has finished execution successfully."""
        self.state = TaskState.TERMINATED
        self.remaining_time = 0

    def fault(self):
        """Record a fault; if max retries exceeded, permanently terminate."""
        self.recovery_attempts += 1
        self.state = TaskState.FAULT

    def try_recover(self) -> bool:
        """
        Attempt fault recovery.
        Returns True if the task recovers (back to READY),
        False if it is permanently terminated.
        """
        if self.recovery_attempts <= self._max_recovery:
            self.state = TaskState.READY
            return True
        self.state = TaskState.TERMINATED
        return False

    # ------------------------------------------------------------------ #
    #  Physics-informed execution                                          #
    # ------------------------------------------------------------------ #

    def execute(self, time_slice: int, system_state: dict | None = None) -> float:
        """
        Execute for at most `time_slice` ticks.

        Fault probability is computed from real system state:
          - Base risk from task type (hardware dependency)
          - Memory pressure amplifier: high pressure → more faults
          - Deadline urgency: close to deadline → rushed execution → more faults
          - Critical tasks: higher stakes, slightly higher fault exposure

        This is the key difference from random.random() faults:
        the AI model trained on these samples learns *real* correlations.

        Returns the actual execution time consumed.
        """
        assert self.state == TaskState.RUNNING, \
            f"Task {self.tid}: execute() called in state {self.state}"

        exec_time = min(time_slice, self.remaining_time, random.uniform(0.8 * time_slice, time_slice))
        self.remaining_time -= time_slice

        # --- Compute physics-informed fault probability ---
        base_risk = TASK_TYPE_RISK.get(self.task_type, 0.05)

        memory_pressure = 1.0
        if system_state:
            available_mem = system_state.get("available_memory", 100)
            if available_mem < 15:
                memory_pressure = 3.5   # severe pressure → fault 3.5× more likely
            elif available_mem < 30:
                memory_pressure = 2.0
            elif available_mem < 50:
                memory_pressure = 1.3

        deadline_urgency = 1.0
        if self.deadline and system_state:
            current_time = system_state.get("current_time", 0)
            slack = self.deadline - current_time
            if slack <= 0:
                deadline_urgency = 4.0   # overdue: very high risk
            elif slack < 5:
                deadline_urgency = 2.5
            elif slack < 10:
                deadline_urgency = 1.4

        critical_factor = 1.2 if self.critical else 1.0
        
        # Scenario multiplier: Survival mode is much more dangerous
        scenario_factor = 1.0
        if system_state:
            mode = system_state.get("mission_mode", "Connected")
            if mode == "Survival":
                scenario_factor = 2.5
            elif mode == "Connected":
                scenario_factor = 0.8  # Link helps stabilization
                
        fault_prob = base_risk * memory_pressure * deadline_urgency * critical_factor * scenario_factor
        fault_prob = min(fault_prob, 0.55)   # cap at 55%

        if random.random() < fault_prob:
            self.fault()
        # else: remain RUNNING; caller transitions to READY or TERMINATED

        return exec_time

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def is_done(self) -> bool:
        return self.remaining_time <= 0

    def missed_deadline(self, current_time: int) -> bool:
        return self.deadline is not None and current_time > self.deadline

    def fault_probability(self, system_state: dict) -> float:
        """Return the current fault probability for this task (used by AI advisor)."""
        base_risk = TASK_TYPE_RISK.get(self.task_type, 0.05)
        available_mem = system_state.get("available_memory", 100)
        current_time = system_state.get("current_time", 0)

        memory_factor = 1.0
        if available_mem < 15:
            memory_factor = 3.5
        elif available_mem < 30:
            memory_factor = 2.0
        elif available_mem < 50:
            memory_factor = 1.3

        urgency = 1.0
        if self.deadline:
            slack = self.deadline - current_time
            if slack <= 0:
                urgency = 4.0
            elif slack < 5:
                urgency = 2.5
            elif slack < 10:
                urgency = 1.4

        # Factor in mission mode
        scenario_factor = 1.0
        mode = system_state.get("mission_mode", "Connected")
        if mode == "Survival":
            scenario_factor = 2.5
        elif mode == "Connected":
            scenario_factor = 0.8

        return min(base_risk * memory_factor * urgency * (1.2 if self.critical else 1.0) * scenario_factor, 0.55)

    def __repr__(self) -> str:
        return (
            f"Task(id={self.tid}, type={self.task_type}, prio={self.effective_priority}, "
            f"remaining={self.remaining_time}, state={self.state.value}, "
            f"deadline={self.deadline})"
        )