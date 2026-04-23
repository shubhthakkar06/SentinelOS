from __future__ import annotations

"""
sentinel_os/components/task_generator.py
------------------------------------------
AUV-specific process generator for SentinelOS.

Generates realistic AUV subsystem processes:
  - 15 distinct AUV task types with proper criticality
  - Mission-phase-aware generation (different tasks at different depths)
  - Persistent tasks auto-respawn (Navigation, HullIntegrity, etc.)
  - Survival mode reduces non-critical task spawning
"""

import random
from sentinel_os.core.task import (
    Task, PERSISTENT_TASKS, TASK_TYPE_RISK,
    TASK_ENERGY_DRAW, TASK_MEMORY_REQ,
)


# Task types grouped by subsystem
CORE_SUBSYSTEMS = [
    "Navigation", "DepthControl", "HullIntegrity",
    "BatteryMonitor", "ThermalRegulation",
]

PERCEPTION_SUBSYSTEMS = [
    "SonarPing", "ObstacleAvoidance", "Hydrophone",
]

PROPULSION_SUBSYSTEMS = [
    "ThrusterControl", "BallastPump",
]

COMMS_SUBSYSTEMS = [
    "EncryptedComms", "GPSSync", "DataLogging",
]

MISSION_SUBSYSTEMS = [
    "MissionPayload", "O2Scrubber",
]

ALL_SUBSYSTEMS = (
    CORE_SUBSYSTEMS + PERCEPTION_SUBSYSTEMS +
    PROPULSION_SUBSYSTEMS + COMMS_SUBSYSTEMS + MISSION_SUBSYSTEMS
)

# Criticality map
CRITICAL_TASKS = {
    "Navigation", "DepthControl", "HullIntegrity",
    "O2Scrubber", "BatteryMonitor", "ThermalRegulation",
}

# Burst time ranges per task type
BURST_TIMES = {
    "Navigation":        (6, 15),
    "ThrusterControl":   (3, 8),
    "DepthControl":      (5, 12),
    "BallastPump":       (4, 10),
    "SonarPing":         (3, 7),
    "ObstacleAvoidance": (5, 14),
    "Hydrophone":        (4, 8),
    "GPSSync":           (2, 5),
    "HullIntegrity":     (8, 20),
    "O2Scrubber":        (6, 12),
    "ThermalRegulation": (5, 10),
    "EncryptedComms":    (3, 8),
    "DataLogging":       (2, 6),
    "BatteryMonitor":    (4, 8),
    "MissionPayload":    (6, 16),
}

# Priority ranges per task type (1-10, higher = more important)
PRIORITY_RANGES = {
    "Navigation":        (7, 9),
    "ThrusterControl":   (6, 8),
    "DepthControl":      (7, 9),
    "BallastPump":       (5, 7),
    "SonarPing":         (4, 6),
    "ObstacleAvoidance": (6, 8),
    "Hydrophone":        (3, 5),
    "GPSSync":           (3, 5),
    "HullIntegrity":     (8, 10),
    "O2Scrubber":        (8, 10),
    "ThermalRegulation": (6, 8),
    "EncryptedComms":    (4, 6),
    "DataLogging":       (2, 4),
    "BatteryMonitor":    (7, 9),
    "MissionPayload":    (5, 7),
}


class TaskGenerator:
    """
    Generates AUV process tasks based on mission state.
    """

    def __init__(self):
        self.task_id = 0
        self._active_persistent: set = set()  # track active persistent tasks by type

    def initialize_services(self) -> list:
        """Create the initial set of long-lived CORE services."""
        services = []
        for task_type in PERSISTENT_TASKS:
            task = self._create_task(task_type, 0, 0)
            services.append(task)
            self._active_persistent.add(task_type)
        return services

    def generate_task(self, current_time: int, system_state: dict | None = None) -> list:
        """
        Generate new AUV tasks for this tick.
        Considers mission mode, depth, and survival phase.
        """
        tasks = []
        mode = "Connected"
        depth = 0
        survival_phase = 0

        if system_state:
            mode = system_state.get("mission_mode", "Connected")
            depth = system_state.get("depth", 0)
            survival_phase = system_state.get("survival_phase", 0)

        # 1. Stochastic Job generation (Transient work only)
        # Base rate: 30% chance per tick; reduced in survival mode
        gen_rate = 0.30
        if survival_phase >= 4:
            gen_rate = 0.0  # Dead ship — no new tasks
        elif survival_phase >= 3:
            gen_rate = 0.05
        elif survival_phase >= 2:
            gen_rate = 0.10
        elif survival_phase >= 1:
            gen_rate = 0.15

        if random.random() < gen_rate:
            # Choose transient task type based on depth and mode
            # Exclude core services from stochastic spawning
            candidates = [t for t in self._get_candidates(depth, survival_phase) if t not in PERSISTENT_TASKS]
            if candidates:
                task_type = random.choice(candidates)
                task = self._create_task(task_type, current_time, depth)
                tasks.append(task)

        # 3. Occasional second task (busy system feel)
        if random.random() < 0.10 and survival_phase < 2:
            task_type = random.choice(ALL_SUBSYSTEMS)
            task = self._create_task(task_type, current_time, depth)
            tasks.append(task)

        return tasks

    def mark_completed(self, task_type: str):
        """Mark a persistent task type as no longer active (so it respawns)."""
        self._active_persistent.discard(task_type)

    def _create_task(self, task_type: str, current_time: int, depth: float) -> Task:
        """Create a task with appropriate parameters for its type."""
        prio_lo, prio_hi = PRIORITY_RANGES.get(task_type, (3, 7))
        burst_lo, burst_hi = BURST_TIMES.get(task_type, (4, 12))

        task = Task(
            tid=self.task_id,
            task_type=task_type,
            base_priority=random.randint(prio_lo, prio_hi),
            deadline=current_time + random.randint(15, 40),
            critical=(task_type in CRITICAL_TASKS),
            burst_time=random.randint(burst_lo, burst_hi),
        )
        task.created_at = current_time
        task.energy_usage = TASK_ENERGY_DRAW.get(task_type, 1.0)

        self.task_id += 1
        return task

    def _get_candidates(self, depth: float, survival_phase: int) -> list:
        """Get task types appropriate for current conditions."""
        candidates = []

        # Core always available
        candidates.extend(CORE_SUBSYSTEMS)

        # Perception: more at depth
        if depth > 20:
            candidates.extend(PERCEPTION_SUBSYSTEMS)
        else:
            candidates.append("SonarPing")  # sonar always useful

        # Propulsion: always needed
        candidates.extend(PROPULSION_SUBSYSTEMS)

        # Comms: GPS only near surface
        if depth < 30:
            candidates.append("GPSSync")
        candidates.append("DataLogging")
        if depth < 200:
            candidates.append("EncryptedComms")

        # Mission
        candidates.extend(MISSION_SUBSYSTEMS)

        # Survival: filter to critical only
        if survival_phase >= 3:
            candidates = [t for t in candidates if t in CRITICAL_TASKS]
        elif survival_phase >= 2:
            candidates = [t for t in candidates if t in CRITICAL_TASKS or t in CORE_SUBSYSTEMS]

        return candidates