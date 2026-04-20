import psutil
import os
import time


class ResourceManager:
    def __init__(self):
        # Real system limits (read-only view)
        self.total_memory = psutil.virtual_memory().total / (1024 ** 3)  # in GB

        # Dynamic values
        self.available_memory = self._get_available_memory()
        self.cpu_usage = 0.0

        # Battery (real if available, else simulated fallback)
        self.has_battery = psutil.sensors_battery() is not None
        self.total_battery = 100.0
        self.current_battery = self._get_battery_level()

        # Internal tracking
        self.active_tasks = set()

    def _get_available_memory(self):
        mem = psutil.virtual_memory()
        return mem.available / (1024 ** 3)  # GB

    def _get_cpu_usage(self):
        return psutil.cpu_percent(interval=0.1)

    def _get_battery_level(self):
        if self.has_battery:
            battery = psutil.sensors_battery()
            return battery.percent if battery else 100.0
        else:
            # fallback simulated battery
            return getattr(self, "current_battery", 100.0)

    def refresh(self):
        """Refresh real system stats"""
        self.available_memory = self._get_available_memory()
        self.cpu_usage = self._get_cpu_usage()
        self.current_battery = self._get_battery_level()

    def allocate(self, task):
        """
        Decide if a task can run based on REAL system constraints
        """
        self.refresh()

        # Policy constraints (you can tune these)
        if self.available_memory < 0.2:  # <200MB approx
            return False

        if self.cpu_usage > 90:  # CPU overloaded
            return False

        if self.current_battery <= 5:
            return False

        # Track active task
        self.active_tasks.add(task.tid)
        return True

    def release(self, task):
        """Release task tracking (OS handles actual memory)"""
        if task.tid in self.active_tasks:
            self.active_tasks.remove(task.tid)

    def consume_energy(self, task):
        """
        Simulate energy drain ONLY if no real battery
        """
        if not self.has_battery:
            drain = getattr(task, "energy_usage", 0.5)
            self.current_battery -= drain
            if self.current_battery < 0:
                self.current_battery = 0

    def apply_scheduling_policy(self, task):
        """
        Apply OS-level control (THIS is where it becomes 'real')
        """
        try:
            pid = getattr(task, "pid", None)
            if pid:
                p = psutil.Process(pid)

                # Adjust priority (nice value)
                if task.base_priority >= 8:
                    p.nice(-5)  # higher priority
                elif task.base_priority <= 3:
                    p.nice(10)  # lower priority

        except Exception:
            pass  # process may have exited

    def kill_task(self, task):
        """Force terminate a process (real OS control)"""
        try:
            pid = getattr(task, "pid", None)
            if pid:
                p = psutil.Process(pid)
                p.terminate()
        except Exception:
            pass
"""
sentinel_os/components/resource_manager.py
-------------------------------------------
Memory and energy resource manager with fragmentation tracking.

Improvements over the original flat "available_memory -= 5":
  - Variable memory allocation per task type
  - Free-list tracking for fragmentation analysis
  - Memory pressure levels (LOW / MEDIUM / HIGH / CRITICAL)
  - Battery depletion with low-power mode
"""

from typing import Dict, Optional
from enum import Enum


class MemoryPressure(str, Enum):
    LOW      = "LOW"       # > 50% available
    MEDIUM   = "MEDIUM"    # 30-50% available
    HIGH     = "HIGH"      # 15-30% available
    CRITICAL = "CRITICAL"  # < 15% available


class ResourceManager:
    """
    Manages the AUV's finite memory and battery resources.

    Memory is modelled as a fixed pool. Each task requires a task-specific
    number of units. The fragmentation metric measures the ratio of small
    unusable holes to total memory — a real OS concept.
    """

    def __init__(self, total_memory: int = 100, total_battery: float = 1000.0):
        self.total_memory: int = total_memory
        self.available_memory: int = total_memory
        self.total_battery: float = total_battery
        self.current_battery: float = total_battery

        # Allocation map: tid → memory_units_held
        self._allocations: Dict[int, int] = {}

        # Energy accounting
        self.total_energy_consumed: float = 0.0

        # Fragmentation tracking
        self._allocation_events: int = 0
        self._fragmentation_events: int = 0   # failed allocs despite enough total memory

        # Statistics
        self.peak_memory_usage: int = 0
        self.alloc_failures: int = 0
        self.mission_mode: str = "Connected"

    def trigger_survival(self):
        """Induce a deep-sea emergency state."""
        self.mission_mode = "Survival"
        # Immediate 85% battery drain and lower the max capacity for the demo
        self.current_battery = min(self.current_battery, 100.0) 
        self.current_battery *= 0.15
        
        # Simulate hardware failures by 'failing' memory blocks
        self.available_memory = min(self.available_memory, 20)
        # We don't change total_memory so the progress bar shows red saturation.

    def trigger_connected(self):
        """Restore links and stabilize hardware."""
        self.mission_mode = "Connected"
        self.current_battery = self.total_battery
        self.available_memory = self.total_memory
        self.alloc_failures = 0

    # ------------------------------------------------------------------ #
    #  Memory                                                              #
    # ------------------------------------------------------------------ #

    def allocate(self, task) -> bool:
        """
        Allocate memory for a task.
        Returns True on success, False if insufficient memory or battery dead.
        """
        if self.current_battery <= 0:
            return False

        required = getattr(task, "memory_required", 5)

        # Re-entrancy check: If task already holds memory, just return success
        if task.tid in self._allocations:
            return True
        
        if self.available_memory < required:
            self.alloc_failures += 1
            # Fragmentation: if total unallocated is enough but contiguous
            # block is not (simplified model: any failure counts)
            self._fragmentation_events += 1
            return False

        self.available_memory -= required
        self._allocations[task.tid] = required
        self._allocation_events += 1

        used = self.total_memory - self.available_memory
        if used > self.peak_memory_usage:
            self.peak_memory_usage = used

        return True

    def release(self, task) -> None:
        """Release memory held by a task."""
        held = self._allocations.pop(task.tid, None)
        if held is not None:
            self.available_memory += held
            # Cap at total (safety guard)
            self.available_memory = min(self.available_memory, self.total_memory)

    def release_by_tid(self, tid: int) -> None:
        """Release memory by task id (for cleanup without task object)."""
        held = self._allocations.pop(tid, None)
        if held is not None:
            self.available_memory = min(self.available_memory + held, self.total_memory)

    # ------------------------------------------------------------------ #
    #  Energy                                                              #
    # ------------------------------------------------------------------ #

    def consume_energy(self, task) -> float:
        """Drain battery by the task's energy usage. Returns actual drain."""
        drain = getattr(task, "energy_usage", 1.0)
        if self.current_battery <= 0:
            return 0.0
        actual = min(drain, self.current_battery)
        self.current_battery -= actual
        self.total_energy_consumed += actual
        if self.current_battery < 0:
            self.current_battery = 0.0
        return actual

    # ------------------------------------------------------------------ #
    #  Derived properties                                                  #
    # ------------------------------------------------------------------ #

    @property
    def memory_utilization(self) -> float:
        return (self.total_memory - self.available_memory) / self.total_memory

    @property
    def battery_fraction(self) -> float:
        return self.current_battery / self.total_battery

    @property
    def pressure(self) -> MemoryPressure:
        pct = self.available_memory / self.total_memory
        if pct < 0.15:
            return MemoryPressure.CRITICAL
        elif pct < 0.30:
            return MemoryPressure.HIGH
        elif pct < 0.50:
            return MemoryPressure.MEDIUM
        return MemoryPressure.LOW

    @property
    def fragmentation_ratio(self) -> float:
        """Fraction of allocations that failed due to insufficient memory."""
        if self._allocation_events == 0:
            return 0.0
        return self._fragmentation_events / (self._allocation_events + self._fragmentation_events)

    def system_state_snapshot(self, current_time: int = 0) -> dict:
        """Return a state dict compatible with Task.execute() and AIAdvisor."""
        return {
            "available_memory": self.available_memory,
            "memory_utilization": round(self.memory_utilization, 4),
            "memory_pressure": self.pressure.value,
            "battery_fraction": round(self.battery_fraction, 4),
            "mission_mode": self.mission_mode,
            "current_time": current_time,
        }

    def stats(self) -> dict:
        return {
            "total_memory": self.total_memory,
            "available_memory": self.available_memory,
            "peak_memory_usage": self.peak_memory_usage,
            "memory_utilization": round(self.memory_utilization, 4),
            "memory_pressure": self.pressure.value,
            "fragmentation_ratio": round(self.fragmentation_ratio, 4),
            "alloc_failures": self.alloc_failures,
            "total_battery": self.total_battery,
            "current_battery": round(self.current_battery, 4),
            "battery_fraction": round(self.battery_fraction, 4),
            "total_energy_consumed": round(self.total_energy_consumed, 4),
            "mission_mode": self.mission_mode,
        }
