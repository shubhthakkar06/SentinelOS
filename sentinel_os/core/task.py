from __future__ import annotations

"""
sentinel_os/core/task.py
-------------------------
Process model for SentinelOS AUV Operating System.

Implements a full 7-state process state machine modeled after real RTOS:

    NEW ──► READY ──► RUNNING ──► TERMINATED (success)
                         │
                         ├──► BLOCKED   (waiting on resource/lock)
                         │       └──► READY   (resource freed)
                         │
                         ├──► WAITING   (I/O wait: sonar, comms, sensor)
                         │       └──► READY   (I/O complete)
                         │
                         ├──► SUSPENDED (frozen by operator or kernel)
                         │       └──► READY   (resumed)
                         │
                         └──► FAULT     (hardware/software fault)
                                 ├──► READY   (recovered)
                                 └──► TERMINATED (unrecoverable)

Key design: Faults are driven by SYSTEM STATE (memory pressure, depth,
battery temperature, deadline proximity) — not bare random dice rolls.
"""

import random
from enum import Enum


class TaskState(str, Enum):
    NEW        = "NEW"
    READY      = "READY"
    RUNNING    = "RUNNING"
    BLOCKED    = "BLOCKED"       # waiting on resource / lock
    WAITING    = "WAITING"       # I/O wait (sonar return, comms ack, sensor read)
    SUSPENDED  = "SUSPENDED"     # frozen by operator or survival-mode kernel
    FAULT      = "FAULT"         # transient hardware/software fault
    TERMINATED = "TERMINATED"    # completed or permanently failed


# ═══════════════════════════════════════════════════════════════════════
#  AUV Task Types — 15 realistic subsystems
# ═══════════════════════════════════════════════════════════════════════

TASK_TYPE_RISK: dict = {
    # Propulsion & Navigation
    "Navigation":        0.03,   # INS + Kalman filter, well-tested
    "ThrusterControl":   0.06,   # actuator-dependent, seal risk at depth
    "DepthControl":      0.07,   # ballast + thruster, depth-pressure sensitive
    "BallastPump":       0.05,   # mechanical pump, failure prone at depth

    # Perception & Sensing
    "SonarPing":         0.05,   # I/O bound, acoustic transducer
    "ObstacleAvoidance": 0.08,   # sensor fusion, higher computational risk
    "Hydrophone":        0.04,   # passive listening, low risk
    "GPSSync":           0.03,   # surface-only, fails at depth

    # Life Support & Hull
    "HullIntegrity":     0.09,   # critical — pressure sensor monitoring
    "O2Scrubber":        0.04,   # life support, must not fail
    "ThermalRegulation": 0.06,   # cooling system, overheats under load

    # Communications & Data
    "EncryptedComms":    0.05,   # crypto overhead, signal attenuation
    "DataLogging":       0.02,   # write to flash, low risk
    "BatteryMonitor":    0.02,   # pure computation, lowest risk

    # Weapons/Mission (if applicable)
    "MissionPayload":    0.07,   # mission-specific sensor/payload
}

TASK_MEMORY_REQ: dict = {
    "Navigation":        10,
    "ThrusterControl":   6,
    "DepthControl":      7,
    "BallastPump":       4,
    "SonarPing":         8,
    "ObstacleAvoidance": 14,
    "Hydrophone":        5,
    "GPSSync":           3,
    "HullIntegrity":     6,
    "O2Scrubber":        4,
    "ThermalRegulation": 5,
    "EncryptedComms":    12,
    "DataLogging":       3,
    "BatteryMonitor":    2,
    "MissionPayload":    10,
}

# Tasks that auto-respawn when completed (critical subsystems)
PERSISTENT_TASKS = {
    "Navigation", "DepthControl", "HullIntegrity",
    "BatteryMonitor", "ThermalRegulation", "O2Scrubber",
}

# Tasks that require I/O wait phases
IO_BOUND_TASKS = {
    "SonarPing", "Hydrophone", "GPSSync", "EncryptedComms", "DataLogging",
}

# Energy draw per task type (watts equivalent)
TASK_ENERGY_DRAW: dict = {
    "Navigation":        1.2,
    "ThrusterControl":   3.5,
    "DepthControl":      2.0,
    "BallastPump":       2.8,
    "SonarPing":         1.8,
    "ObstacleAvoidance": 1.5,
    "Hydrophone":        0.6,
    "GPSSync":           0.8,
    "HullIntegrity":     0.5,
    "O2Scrubber":        1.0,
    "ThermalRegulation": 1.5,
    "EncryptedComms":    1.3,
    "DataLogging":       0.4,
    "BatteryMonitor":    0.3,
    "MissionPayload":    2.0,
}


class Task:
    """
    Represents a single AUV process with a 7-state machine
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

        # Architecture: Service vs Job
        # Services are long-lived (Navigation, HullIntegrity).
        # Jobs are transient commands or payloads.
        self.is_service: bool = (task_type in PERSISTENT_TASKS)
        self.mailbox: list = []  # commands for the service to process

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
        self.energy_usage: float = TASK_ENERGY_DRAW.get(task_type, 1.0)

        # Scheduling metadata
        self.waiting_time: int = 0       # accumulated ticks waiting in queue
        self.effective_priority: int = base_priority

        # Lock state (for priority inversion demo)
        self.held_lock: str | None = None
        self.waiting_for_lock: str | None = None

        # I/O wait tracking
        self.io_wait_remaining: int = 0  # ticks of I/O wait left
        self.io_device: str | None = None  # which device it's waiting on

        # Suspension
        self.suspended_by: str | None = None  # "operator" or "kernel"
        self._pre_suspend_state: TaskState | None = None

        # Fault Tracking
        self.fault_history: set[str] = set()
        self.total_faults: int = 0

        # AI & Diagnostics
        self.ai_boost: int = 0
        self.ai_advice_cache: dict | None = None  # { 'boost': int, 'reason': str, 'ts': int }
        self.intervention_outcome: str | None = None
        self.blocked_reason: str | None = None

        # Runtime stats
        self.cpu_ticks: int = 0          # total ticks spent running
        self.created_at: int = 0         # simulation time of creation

    # ------------------------------------------------------------------ #
    #  State transitions                                                   #
    # ------------------------------------------------------------------ #

    def ready(self):
        """Transition to READY (from NEW, BLOCKED, WAITING, SUSPENDED, or recovered FAULT)."""
        self.state = TaskState.READY
        self.blocked_reason = None
        self.io_device = None

    def start_running(self):
        """Transition to RUNNING when the scheduler dispatches this task."""
        assert self.state == TaskState.READY, \
            f"Task {self.tid}: can only run from READY, currently {self.state}"
        self.state = TaskState.RUNNING

    def block(self, reason: str = "RES"):
        """Task is blocked waiting for a resource or lock."""
        self.state = TaskState.BLOCKED
        self.blocked_reason = reason

    def wait_io(self, device: str = "SENSOR", ticks: int = 0):
        """Task enters I/O wait state (distinct from resource-blocked)."""
        self.state = TaskState.WAITING
        self.io_device = device
        self.io_wait_remaining = ticks if ticks > 0 else random.randint(2, 5)

    def tick_io_wait(self) -> bool:
        """Decrement I/O wait counter. Returns True if I/O is complete."""
        if self.io_wait_remaining > 0:
            self.io_wait_remaining -= 1
        return self.io_wait_remaining <= 0

    def suspend(self, by: str = "operator"):
        """Freeze this process. Can be done by operator or kernel survival mode."""
        if self.state in (TaskState.TERMINATED, TaskState.SUSPENDED):
            return
        self._pre_suspend_state = self.state
        self.state = TaskState.SUSPENDED
        self.suspended_by = by

    def resume(self) -> bool:
        """Resume a suspended process. Returns True on success."""
        if self.state != TaskState.SUSPENDED:
            return False
        # Restore to READY (safest re-entry point)
        self.state = TaskState.READY
        self.suspended_by = None
        self._pre_suspend_state = None
        return True

    def terminate(self):
        """Task has finished execution successfully."""
        if self.is_service:
            # Services don't terminate; they reset for the next period/command
            self.state = TaskState.READY
            self.remaining_time = self.burst_time
            return

        self.state = TaskState.TERMINATED
        self.remaining_time = 0

    def fault(self):
        """Record a fault; if max retries exceeded, permanently terminate."""
        self.recovery_attempts += 1
        self.total_faults += 1
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
          - Memory pressure amplifier
          - Deadline urgency
          - Depth pressure factor (deeper = more risk)
          - Battery temperature factor
          - Mission mode factor

        Returns the actual execution time consumed.
        """
        assert self.state == TaskState.RUNNING, \
            f"Task {self.tid}: execute() called in state {self.state}"

        exec_time = min(time_slice, self.remaining_time, random.uniform(0.8 * time_slice, time_slice))
        self.remaining_time -= time_slice
        self.cpu_ticks += 1

        # Check if this is an I/O-bound task that should enter WAITING
        if self.task_type in IO_BOUND_TASKS and random.random() < 0.15:
            io_devices = {
                "SonarPing": "SONAR_XDCR",
                "Hydrophone": "HYDRO_ARRAY",
                "GPSSync": "GPS_ANTENNA",
                "EncryptedComms": "COMMS_RADIO",
                "DataLogging": "FLASH_NAND",
            }
            self.wait_io(
                device=io_devices.get(self.task_type, "SENSOR"),
                ticks=random.randint(2, 4)
            )
            return exec_time

        # --- Compute physics-informed fault probability ---
        base_risk = TASK_TYPE_RISK.get(self.task_type, 0.05)

        memory_pressure = 1.0
        if system_state:
            available_mem = system_state.get("available_memory", 100)
            if available_mem < 15:
                memory_pressure = 3.5
            elif available_mem < 30:
                memory_pressure = 2.0
            elif available_mem < 50:
                memory_pressure = 1.3

        deadline_urgency = 1.0
        if self.deadline and system_state:
            current_time = system_state.get("current_time", 0)
            slack = self.deadline - current_time
            if slack <= 0:
                deadline_urgency = 4.0
            elif slack < 5:
                deadline_urgency = 2.5
            elif slack < 10:
                deadline_urgency = 1.4

        critical_factor = 1.2 if self.critical else 1.0

        # Depth pressure: deeper = more risk
        depth_factor = 1.0
        if system_state:
            depth = system_state.get("depth", 0)
            if depth > 400:
                depth_factor = 3.0
            elif depth > 300:
                depth_factor = 2.0
            elif depth > 200:
                depth_factor = 1.5
            elif depth > 100:
                depth_factor = 1.2

        # Battery temperature: hot cells = more electronic faults
        temp_factor = 1.0
        if system_state:
            batt_temp = system_state.get("battery_temp", 25)
            if batt_temp > 55:
                temp_factor = 3.0
            elif batt_temp > 45:
                temp_factor = 2.0
            elif batt_temp > 35:
                temp_factor = 1.3

        # Mission mode factor
        scenario_factor = 1.0
        if system_state:
            mode = system_state.get("mission_mode", "Connected")
            if mode == "Survival":
                scenario_factor = 2.5
            elif mode == "Connected":
                scenario_factor = 0.8

        fault_prob = (base_risk * memory_pressure * deadline_urgency *
                      critical_factor * depth_factor * temp_factor * scenario_factor)
        fault_prob = min(fault_prob, 0.55)

        if random.random() < fault_prob:
            self.fault()

        return exec_time

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def is_done(self) -> bool:
        return self.remaining_time <= 0

    def missed_deadline(self, current_time: int) -> bool:
        return self.deadline is not None and current_time > self.deadline

    def is_persistent(self) -> bool:
        """Whether this task type auto-respawns on completion."""
        return self.task_type in PERSISTENT_TASKS

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

        depth = system_state.get("depth", 0)
        depth_factor = 1.0 + max(0, depth - 100) / 200

        scenario_factor = 1.0
        mode = system_state.get("mission_mode", "Connected")
        if mode == "Survival":
            scenario_factor = 2.5
        elif mode == "Connected":
            scenario_factor = 0.8

        return min(base_risk * memory_factor * urgency *
                   (1.2 if self.critical else 1.0) * depth_factor * scenario_factor, 0.55)

    def state_label(self) -> str:
        """Human-readable state with reason info."""
        s = self.state.value
        if self.state == TaskState.BLOCKED and self.blocked_reason:
            return f"BLOCKED({self.blocked_reason})"
        elif self.state == TaskState.WAITING and self.io_device:
            return f"WAIT({self.io_device})"
        elif self.state == TaskState.SUSPENDED:
            return f"SUSPENDED({self.suspended_by or '?'})"
        return s

    def __repr__(self) -> str:
        return (
            f"Task(id={self.tid}, type={self.task_type}, prio={self.effective_priority}, "
            f"remaining={self.remaining_time}, state={self.state.value}, "
            f"deadline={self.deadline})"
        )