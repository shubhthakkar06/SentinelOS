"""
sentinel_os/components/battery.py
-----------------------------------
Realistic Battery Management System (BMS) for the SentinelOS AUV.

Models a lithium-ion battery pack in 2S4P configuration (8 cells):
  - Non-linear discharge curves (voltage sags under load)
  - Per-cell temperature tracking and thermal throttle
  - Cell health degradation over time
  - Depth-pressure effects on thermal dissipation
  - Charge state machine: FULL → NOMINAL → LOW → CRITICAL → EMERGENCY → DEAD
  - Estimated time-to-empty based on rolling average current draw
"""

import random
import math
from enum import Enum
from typing import List


class ChargeState(str, Enum):
    FULL      = "FULL"       # > 80%
    NOMINAL   = "NOMINAL"    # 50-80%
    LOW       = "LOW"        # 25-50%
    CRITICAL  = "CRITICAL"   # 10-25%
    EMERGENCY = "EMERGENCY"  # 3-10%
    DEAD      = "DEAD"       # < 3%


class CellHealth(str, Enum):
    HEALTHY   = "OK"
    DEGRADED  = "DEGRADED"
    FAILING   = "FAILING"
    DEAD      = "DEAD"


class BatteryCell:
    """Single lithium-ion 18650-style cell."""

    # Li-ion voltage curve breakpoints (SOC% → voltage)
    VOLTAGE_CURVE = [
        (100, 4.20), (90, 4.06), (80, 3.97), (70, 3.87),
        (60, 3.80), (50, 3.73), (40, 3.68), (30, 3.62),
        (20, 3.50), (10, 3.30), (5, 3.10), (0, 2.50),
    ]

    def __init__(self, cell_id: int, capacity_ah: float = 3.5):
        self.cell_id = cell_id
        self.capacity_ah = capacity_ah          # Amp-hours nominal
        self.remaining_ah = capacity_ah         # current charge
        self.temperature = 22.0 + random.uniform(-2, 2)  # °C
        self.health = CellHealth.HEALTHY
        self.cycle_count = random.randint(0, 50)
        self.internal_resistance = 0.045 + random.uniform(0, 0.015)  # ohms

        # Degradation accumulator
        self._stress_accumulator = 0.0

    @property
    def soc(self) -> float:
        """State of charge as percentage (0-100)."""
        return max(0, min(100, (self.remaining_ah / self.capacity_ah) * 100))

    @property
    def voltage(self) -> float:
        """Open-circuit voltage based on SOC (non-linear)."""
        soc = self.soc
        # Interpolate from voltage curve
        for i in range(len(self.VOLTAGE_CURVE) - 1):
            soc_hi, v_hi = self.VOLTAGE_CURVE[i]
            soc_lo, v_lo = self.VOLTAGE_CURVE[i + 1]
            if soc_lo <= soc <= soc_hi:
                t = (soc - soc_lo) / (soc_hi - soc_lo) if soc_hi != soc_lo else 0
                return v_lo + t * (v_hi - v_lo)
        return 2.50  # below minimum

    @property
    def voltage_under_load(self) -> float:
        """Voltage with IR drop under typical 2A load."""
        return max(2.5, self.voltage - (self.internal_resistance * 2.0))

    @property
    def is_overheating(self) -> bool:
        return self.temperature > 50.0

    @property
    def is_critical_temp(self) -> bool:
        return self.temperature > 60.0

    def drain(self, amp_hours: float, ambient_temp: float = 20.0, depth: float = 0):
        """
        Drain the cell by amp_hours. Updates temperature based on:
          - I²R heating from internal resistance
          - Ambient cooling (worse at depth due to pressure on hull)
          - Depth pressure reduces cooling efficiency
        """
        if self.health == CellHealth.DEAD:
            return

        self.remaining_ah = max(0, self.remaining_ah - amp_hours)

        # I²R heating (simplified: assume 2A average current)
        heat_generated = (2.0 ** 2) * self.internal_resistance * 0.05
        # Depth reduces cooling (hull insulation + pressure)
        cooling_factor = max(0.3, 1.0 - (depth / 800))
        cooling = (self.temperature - ambient_temp) * 0.02 * cooling_factor

        self.temperature += heat_generated - cooling
        self.temperature = max(ambient_temp - 5, min(75, self.temperature))

        # Stress accumulation → degradation
        if self.temperature > 45:
            self._stress_accumulator += (self.temperature - 45) * 0.001
        if self.remaining_ah < self.capacity_ah * 0.1:
            self._stress_accumulator += 0.005  # deep discharge stress

        # Health transitions
        if self._stress_accumulator > 5.0:
            self.health = CellHealth.DEAD
            self.remaining_ah = 0
        elif self._stress_accumulator > 2.0:
            self.health = CellHealth.FAILING
            self.internal_resistance *= 1.01  # resistance creep
        elif self._stress_accumulator > 0.5:
            self.health = CellHealth.DEGRADED

    def status_icon(self) -> str:
        icons = {
            CellHealth.HEALTHY: "●",
            CellHealth.DEGRADED: "◐",
            CellHealth.FAILING: "◌",
            CellHealth.DEAD: "✗",
        }
        return icons.get(self.health, "?")


class BatteryManagementSystem:
    """
    Full battery pack management for the AUV.

    Pack topology: 2S4P (2 series × 4 parallel)
      - 2 cells in series → ~7.4V nominal per string
      - 4 strings in parallel → 4× capacity
      - 8 cells total
    """

    def __init__(self, cell_count: int = 8, cell_capacity: float = 3.5):
        self.cells: List[BatteryCell] = [
            BatteryCell(i, cell_capacity) for i in range(cell_count)
        ]
        self.cell_count = cell_count
        self.total_capacity_wh = cell_count * cell_capacity * 3.7  # Wh at nominal V

        # Current draw tracking (for ETA calculation)
        self._draw_history: list = []  # recent draws in watts
        self._max_draw_history = 30

        # Thermal throttle state
        self.thermal_throttle_active = False

    # ────────────────────────────────────────────────────────────────────
    #  Pack-level metrics
    # ────────────────────────────────────────────────────────────────────

    @property
    def pack_soc(self) -> float:
        """Overall state of charge (0-100%)."""
        live = [c for c in self.cells if c.health != CellHealth.DEAD]
        if not live:
            return 0.0
        return sum(c.soc for c in live) / len(live)

    @property
    def pack_voltage(self) -> float:
        """Pack voltage (2S config = 2 × cell voltage)."""
        live = [c for c in self.cells if c.health != CellHealth.DEAD]
        if not live:
            return 0.0
        avg_v = sum(c.voltage_under_load for c in live) / len(live)
        return avg_v * 2  # 2S series

    @property
    def avg_temperature(self) -> float:
        live = [c for c in self.cells if c.health != CellHealth.DEAD]
        if not live:
            return 0.0
        return sum(c.temperature for c in live) / len(live)

    @property
    def max_temperature(self) -> float:
        live = [c for c in self.cells if c.health != CellHealth.DEAD]
        if not live:
            return 0.0
        return max(c.temperature for c in live)

    @property
    def healthy_cell_count(self) -> int:
        return sum(1 for c in self.cells if c.health != CellHealth.DEAD)

    @property
    def charge_state(self) -> ChargeState:
        soc = self.pack_soc
        if soc > 80:
            return ChargeState.FULL
        elif soc > 50:
            return ChargeState.NOMINAL
        elif soc > 25:
            return ChargeState.LOW
        elif soc > 10:
            return ChargeState.CRITICAL
        elif soc > 3:
            return ChargeState.EMERGENCY
        return ChargeState.DEAD

    @property
    def estimated_minutes_remaining(self) -> float:
        """ETA based on rolling average power draw."""
        if not self._draw_history:
            return 999.0
        avg_draw = sum(self._draw_history) / len(self._draw_history)
        if avg_draw <= 0:
            return 999.0
        remaining_wh = (self.pack_soc / 100) * self.total_capacity_wh
        hours = remaining_wh / avg_draw
        return hours * 60

    # ────────────────────────────────────────────────────────────────────
    #  Drain & Tick
    # ────────────────────────────────────────────────────────────────────

    def drain(self, watts: float, depth: float = 0, water_temp: float = 4.0):
        """
        Drain the pack by `watts` for one simulation tick.
        Distributes load across healthy cells.
        """
        live_cells = [c for c in self.cells if c.health != CellHealth.DEAD]
        if not live_cells:
            return

        # Thermal throttle: reduce draw if overheating
        if any(c.is_overheating for c in live_cells):
            self.thermal_throttle_active = True
            watts *= 0.6
        else:
            self.thermal_throttle_active = False

        # Track draw
        self._draw_history.append(watts)
        if len(self._draw_history) > self._max_draw_history:
            self._draw_history.pop(0)

        # Convert watts to Ah per cell
        # watts = V × I; at ~3.7V nominal: I = watts / (3.7 * num_live)
        current_per_cell = watts / (3.7 * len(live_cells))
        ah_drain = current_per_cell / 3600  # per tick (assume 1-second ticks)
        # Scale up for simulation speed (each tick = ~10 real seconds)
        ah_drain *= 10

        for cell in live_cells:
            cell.drain(ah_drain, ambient_temp=water_temp, depth=depth)

    def fail_random_cell(self):
        """Simulate a sudden cell failure (for dramatic survival mode events)."""
        healthy = [c for c in self.cells if c.health == CellHealth.HEALTHY]
        if healthy:
            victim = random.choice(healthy)
            victim.health = CellHealth.FAILING
            victim.internal_resistance *= 3
            return victim.cell_id
        return None

    def stats(self) -> dict:
        return {
            "pack_soc": round(self.pack_soc, 1),
            "pack_voltage": round(self.pack_voltage, 2),
            "charge_state": self.charge_state.value,
            "avg_temp": round(self.avg_temperature, 1),
            "max_temp": round(self.max_temperature, 1),
            "healthy_cells": self.healthy_cell_count,
            "total_cells": self.cell_count,
            "thermal_throttle": self.thermal_throttle_active,
            "eta_minutes": round(self.estimated_minutes_remaining, 1),
            "cells": [
                {
                    "id": c.cell_id,
                    "soc": round(c.soc, 1),
                    "voltage": round(c.voltage_under_load, 3),
                    "temp": round(c.temperature, 1),
                    "health": c.health.value,
                    "resistance_mohm": round(c.internal_resistance * 1000, 1),
                }
                for c in self.cells
            ],
        }
