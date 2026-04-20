"""
tests/test_resource_manager.py
--------------------------------
Tests for memory allocation, pressure levels, fragmentation,
and energy tracking in ResourceManager.
"""

import pytest
from sentinel_os.components.resource_manager import ResourceManager, MemoryPressure
from sentinel_os.core.task import Task, TaskState


def make_task(tid, task_type="Navigation", burst_time=10):
    t = Task(tid, task_type, base_priority=5, burst_time=burst_time)
    t.state = TaskState.READY
    return t


class TestMemoryAllocation:
    def test_allocation_reduces_available_memory(self):
        rm = ResourceManager(total_memory=100)
        t = make_task(1, "Navigation")   # requires 8 units
        required = t.memory_required
        rm.allocate(t)
        assert rm.available_memory == 100 - required

    def test_release_restores_memory(self):
        rm = ResourceManager(total_memory=100)
        t = make_task(1)
        rm.allocate(t)
        rm.release(t)
        assert rm.available_memory == 100

    def test_allocation_fails_when_memory_insufficient(self):
        rm = ResourceManager(total_memory=10)
        # Navigation requires 8 units; try to allocate two of them
        t1 = make_task(1, "Navigation")   # 8 units
        t2 = make_task(2, "Navigation")   # 8 units — not enough space
        assert rm.allocate(t1) is True
        assert rm.allocate(t2) is False   # only 2 units left

    def test_allocation_fails_when_battery_dead(self):
        rm = ResourceManager()
        rm.current_battery = 0.0
        t = make_task(1)
        assert rm.allocate(t) is False

    def test_memory_cannot_exceed_total_on_release(self):
        rm = ResourceManager(total_memory=100)
        t = make_task(1)
        rm.allocate(t)
        rm.release(t)
        rm.release(t)   # double-release — should not exceed total
        assert rm.available_memory <= 100

    def test_peak_memory_tracked(self):
        rm = ResourceManager(total_memory=100)
        t1 = make_task(1, "Navigation")   # 8 units
        t2 = make_task(2, "SonarPing")    # 5 units
        rm.allocate(t1)
        rm.allocate(t2)
        assert rm.peak_memory_usage == t1.memory_required + t2.memory_required


class TestMemoryPressure:
    def test_low_pressure_when_mostly_free(self):
        rm = ResourceManager(total_memory=100)
        rm.available_memory = 80
        assert rm.pressure == MemoryPressure.LOW

    def test_medium_pressure(self):
        rm = ResourceManager(total_memory=100)
        rm.available_memory = 40
        assert rm.pressure == MemoryPressure.MEDIUM

    def test_high_pressure(self):
        rm = ResourceManager(total_memory=100)
        rm.available_memory = 20
        assert rm.pressure == MemoryPressure.HIGH

    def test_critical_pressure(self):
        rm = ResourceManager(total_memory=100)
        rm.available_memory = 10
        assert rm.pressure == MemoryPressure.CRITICAL


class TestEnergyTracking:
    def test_energy_consumed_drains_battery(self):
        rm = ResourceManager(total_battery=100.0)
        t = make_task(1)
        t.energy_usage = 10.0
        rm.consume_energy(t)
        assert rm.current_battery == pytest.approx(90.0, rel=1e-3)

    def test_battery_cannot_go_negative(self):
        rm = ResourceManager(total_battery=5.0)
        t = make_task(1)
        t.energy_usage = 100.0
        rm.consume_energy(t)
        assert rm.current_battery == 0.0

    def test_total_energy_consumed_accumulates(self):
        rm = ResourceManager(total_battery=500.0)
        for i in range(5):
            t = make_task(i)
            t.energy_usage = 10.0
            rm.consume_energy(t)
        assert rm.total_energy_consumed == pytest.approx(50.0, rel=1e-3)

    def test_energy_not_consumed_when_battery_dead(self):
        rm = ResourceManager(total_battery=10.0)
        rm.current_battery = 0.0
        t = make_task(1)
        t.energy_usage = 5.0
        drain = rm.consume_energy(t)
        assert drain == 0.0


class TestSystemStateSnapshot:
    def test_snapshot_contains_required_keys(self):
        rm = ResourceManager()
        snap = rm.system_state_snapshot(current_time=42)
        for key in ("available_memory", "memory_utilization", "memory_pressure",
                    "battery_fraction", "current_time"):
            assert key in snap, f"Missing key in snapshot: {key}"

    def test_snapshot_current_time(self):
        rm = ResourceManager()
        snap = rm.system_state_snapshot(current_time=99)
        assert snap["current_time"] == 99
