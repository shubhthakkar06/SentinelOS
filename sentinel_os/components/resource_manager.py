from __future__ import annotations

"""
sentinel_os/components/resource_manager.py
-------------------------------------------
Memory and energy resource manager with fragmentation tracking.

Improvements:
  - Variable memory allocation per task type
  - Free-list tracking for fragmentation analysis
  - Memory pressure levels (LOW / MEDIUM / HIGH / CRITICAL)
  - Integrated BatteryManagementSystem (realistic cell-level BMS)
  - Environment-aware state snapshots
"""

from typing import Dict, Optional
from enum import Enum
from sentinel_os.components.battery import BatteryManagementSystem


class MemoryPressure(str, Enum):
    LOW      = "LOW"       # > 50% available
    MEDIUM   = "MEDIUM"    # 30-50% available
    HIGH     = "HIGH"      # 15-30% available
    CRITICAL = "CRITICAL"  # < 15% available


class ResourceManager:
    """
    Manages the AUV's finite memory and battery resources.
    Memory is modelled as a fixed pool. Battery is managed by the BMS.
    """

    def __init__(self, total_memory: int = 100, total_battery: float = 1000.0):
        self.total_memory: int = total_memory
        self.available_memory: int = total_memory

        # Battery Management System (replaces flat float)
        self.bms = BatteryManagementSystem(cell_count=8, cell_capacity=3.5)

        # Legacy compat: pack SOC mapped to 0-total_battery range
        self._total_battery_scale = total_battery

        # Allocation map: tid → memory_units_held
        self._allocations: Dict[int, int] = {}

        # Energy accounting
        self.total_energy_consumed: float = 0.0

        # Fragmentation tracking
        self._allocation_events: int = 0
        self._fragmentation_events: int = 0

        # Statistics
        self.peak_memory_usage: int = 0
        self.alloc_failures: int = 0
        self.mission_mode: str = "Connected"

        # Survival phase tracking
        self.survival_phase: int = 0
        self._suspended_by_survival: list = []  # tids suspended by kernel

        # Admission Control (Runtime Stability)
        self.max_jobs: int = 12          # Max transient jobs in system
        self.reserved_service_mem: int = 40  # Memory always kept for core services

    # ────────────────────────────────────────────────────────────────────
    #  Battery (delegated to BMS)
    # ────────────────────────────────────────────────────────────────────

    @property
    def total_battery(self) -> float:
        return self._total_battery_scale

    @property
    def current_battery(self) -> float:
        """Map BMS SOC to legacy scale (0 - total_battery)."""
        return (self.bms.pack_soc / 100) * self._total_battery_scale

    @current_battery.setter
    def current_battery(self, value: float):
        """Legacy setter — drain BMS cells proportionally."""
        target_soc = (value / self._total_battery_scale) * 100
        current_soc = self.bms.pack_soc
        if target_soc < current_soc:
            # Drain proportionally
            ratio = target_soc / max(current_soc, 0.01)
            for cell in self.bms.cells:
                cell.remaining_ah *= ratio

    @property
    def battery_fraction(self) -> float:
        return self.bms.pack_soc / 100

    # ────────────────────────────────────────────────────────────────────
    #  Mission Mode
    # ────────────────────────────────────────────────────────────────────

    def trigger_survival(self):
        """Induce autonomous survival mode. Multi-phase degradation begins."""
        self.mission_mode = "Survival"
        self.survival_phase = 1

        # Immediate impact: 40% battery drain (simulating emergency)
        for cell in self.bms.cells:
            cell.remaining_ah *= 0.60

        # Simulate hardware failures by 'failing' memory blocks
        self.available_memory = min(self.available_memory, 40)

        # Random cell damage
        self.bms.fail_random_cell()

    def trigger_connected(self):
        """Restore links and stabilize hardware."""
        self.mission_mode = "Connected"
        self.survival_phase = 0

        # Restore battery (simulating shore power / recharge)
        for cell in self.bms.cells:
            cell.remaining_ah = cell.capacity_ah
            cell.temperature = 22.0
            if cell.health.value != "DEAD":
                from sentinel_os.components.battery import CellHealth
                cell.health = CellHealth.HEALTHY
                cell.internal_resistance = 0.045

        self.available_memory = self.total_memory
        self.alloc_failures = 0
        self._suspended_by_survival = []

    def update_survival_phase(self) -> int:
        """
        Check battery SOC and advance survival phases.
        Returns the current phase (0=normal, 1-5=survival phases).
        """
        if self.mission_mode != "Survival":
            return 0

        soc = self.bms.pack_soc
        old_phase = self.survival_phase

        if soc > 60:
            self.survival_phase = 1   # Link Lost
        elif soc > 35:
            self.survival_phase = 2   # Power Conservation
        elif soc > 15:
            self.survival_phase = 3   # Critical Operations
        elif soc > 5:
            self.survival_phase = 4   # Emergency Ascent
        else:
            self.survival_phase = 5   # Dead Ship

        # Apply phase effects on memory
        phase_memory = {1: 40, 2: 30, 3: 20, 4: 15, 5: 5}
        max_mem = phase_memory.get(self.survival_phase, self.total_memory)
        self.available_memory = min(self.available_memory, max_mem)

        return self.survival_phase

    # ────────────────────────────────────────────────────────────────────
    #  Memory
    # ────────────────────────────────────────────────────────────────────

    def can_admit_task(self, task, current_count: int) -> tuple[bool, str]:
        """
        Decision engine: Should we let this task enter the ready queue?
        Returns (allowed, reason).
        """
        # Services are always admitted (they are core hardware)
        if task.is_service:
            return True, "Core service"
            
        # Backpressure: cap total job count
        if current_count >= self.max_jobs:
            return False, f"Job limit reached ({self.max_jobs})"
            
        # Backpressure: memory scarcity
        required = getattr(task, "memory_required", 5)
        # Transient jobs cannot touch reserved service memory
        if (self.available_memory - required) < self.reserved_service_mem:
            return False, f"Memory reserved for core services (Pressure: {self.pressure.value})"
            
        return True, "OK"

    def allocate(self, task) -> bool:
        """Allocate memory for a task. Returns True on success."""
        if self.bms.pack_soc <= 0:
            return False

        required = getattr(task, "memory_required", 5)

        # Re-entrancy check
        if task.tid in self._allocations:
            return True

        # Safety check: available_memory should not go below 0
        if self.available_memory < required:
            self.alloc_failures += 1
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
            self.available_memory = min(self.available_memory, self.total_memory)

    def release_by_tid(self, tid: int) -> None:
        """Release memory by task id."""
        held = self._allocations.pop(tid, None)
        if held is not None:
            self.available_memory = min(self.available_memory + held, self.total_memory)

    # ────────────────────────────────────────────────────────────────────
    #  Energy
    # ────────────────────────────────────────────────────────────────────

    def consume_energy(self, task, depth: float = 0, water_temp: float = 4.0) -> float:
        """Drain battery via BMS. Returns actual energy consumed (watts)."""
        draw_watts = getattr(task, "energy_usage", 1.0)

        # Survival mode: throttle power draw in later phases
        if self.survival_phase >= 3:
            draw_watts *= 0.5
        elif self.survival_phase >= 2:
            draw_watts *= 0.7

        self.bms.drain(draw_watts, depth=depth, water_temp=water_temp)
        self.total_energy_consumed += draw_watts
        return draw_watts

    # ────────────────────────────────────────────────────────────────────
    #  Derived properties
    # ────────────────────────────────────────────────────────────────────

    @property
    def memory_utilization(self) -> float:
        return (self.total_memory - self.available_memory) / self.total_memory

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
        if self._allocation_events == 0:
            return 0.0
        return self._fragmentation_events / (self._allocation_events + self._fragmentation_events)

    def system_state_snapshot(self, current_time: int = 0, env_data: dict | None = None) -> dict:
        """Return a state dict compatible with Task.execute() and AIAdvisor."""
        state = {
            "available_memory": self.available_memory,
            "memory_utilization": round(self.memory_utilization, 4),
            "memory_pressure": self.pressure.value,
            "battery_fraction": round(self.battery_fraction, 4),
            "battery_soc": round(self.bms.pack_soc, 1),
            "battery_temp": round(self.bms.avg_temperature, 1),
            "charge_state": self.bms.charge_state.value,
            "thermal_throttle": self.bms.thermal_throttle_active,
            "mission_mode": self.mission_mode,
            "survival_phase": self.survival_phase,
            "current_time": current_time,
            "depth": 0,
        }
        # Merge environment data
        if env_data:
            state.update(env_data)
        return state

    def stats(self) -> dict:
        bms_stats = self.bms.stats()
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
            "battery_soc": bms_stats["pack_soc"],
            "pack_voltage": bms_stats["pack_voltage"],
            "charge_state": bms_stats["charge_state"],
            "avg_temp": bms_stats["avg_temp"],
            "max_temp": bms_stats["max_temp"],
            "healthy_cells": bms_stats["healthy_cells"],
            "total_cells": bms_stats["total_cells"],
            "thermal_throttle": bms_stats["thermal_throttle"],
            "eta_minutes": bms_stats["eta_minutes"],
            "total_energy_consumed": round(self.total_energy_consumed, 4),
            "mission_mode": self.mission_mode,
            "survival_phase": self.survival_phase,
        }
