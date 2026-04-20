"""
tests/test_metrics.py
----------------------
Tests for the KPI metrics engine.
Verifies correct calculation of derived metrics.
"""

import pytest
from sentinel_os.monitoring.metrics import Metrics


def make_metrics(**kwargs):
    m = Metrics()
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


class TestMetricsBasic:
    def test_initial_state(self):
        m = Metrics()
        assert m.tasks_completed == 0
        assert m.cpu_utilization == 0.0
        assert m.deadline_miss_rate == 0.0

    def test_cpu_utilization(self):
        m = Metrics()
        m.record_step({"time": 0, "task_running": True})
        m.record_step({"time": 1, "task_running": True})
        m.record_step({"time": 2, "task_running": False})
        assert m.cpu_utilization == pytest.approx(2 / 3, rel=1e-3)

    def test_deadline_miss_rate(self):
        m = Metrics()
        m.record_task_arrival(1, 0)
        m.record_task_arrival(2, 0)
        m.record_task_completed(1, time=10, missed_deadline=True)
        m.record_task_completed(2, time=20, missed_deadline=False)
        assert m.deadline_miss_rate == pytest.approx(0.5, rel=1e-3)

    def test_task_completion_rate(self):
        m = Metrics()
        m.record_task_arrival(1, 0)
        m.record_task_arrival(2, 0)
        m.record_task_completed(1, 10, missed_deadline=False)
        m.record_task_fault_terminated(2, 15)
        assert m.task_completion_rate == pytest.approx(0.5, rel=1e-3)

    def test_throughput(self):
        m = Metrics()
        for i in range(10):
            m.record_step({"time": i, "task_running": True})
        for i in range(5):
            m.record_task_arrival(i, 0)
            m.record_task_completed(i, i * 2, missed_deadline=False)
        # 5 tasks completed in 10 steps → throughput = 0.5
        assert m.throughput == pytest.approx(0.5, rel=1e-3)

    def test_average_waiting_time(self):
        m = Metrics()
        m.record_task_waiting(1, 10)
        m.record_task_waiting(2, 20)
        m.record_task_waiting(3, 30)
        assert m.average_waiting_time == pytest.approx(20.0, rel=1e-3)

    def test_average_turnaround_time(self):
        m = Metrics()
        m.record_task_arrival(1, 0)
        m.record_task_arrival(2, 5)
        m.record_task_completed(1, 10, False)   # turnaround = 10
        m.record_task_completed(2, 20, False)   # turnaround = 15
        assert m.average_turnaround_time == pytest.approx(12.5, rel=1e-3)

    def test_fault_rate(self):
        m = Metrics()
        for i in range(100):
            m.record_step({"time": i, "task_running": True})
        for j in range(10):
            m.record_fault({"fault_type": "RESOURCE_FAILURE", "task_id": j, "time": j})
        assert m.fault_rate == pytest.approx(0.1, rel=1e-3)

    def test_ai_precision(self):
        m = Metrics()
        # 3 interventions, 2 correct
        m.record_ai_intervention(predicted_fault=True,  actual_fault=True)
        m.record_ai_intervention(predicted_fault=True,  actual_fault=False)
        m.record_ai_intervention(predicted_fault=True,  actual_fault=True)
        # precision = 2/3
        assert m.ai_precision == pytest.approx(2 / 3, rel=1e-3)

    def test_ai_precision_none_when_no_interventions(self):
        m = Metrics()
        m.record_ai_intervention(predicted_fault=False, actual_fault=True)
        assert m.ai_precision is None

    def test_energy_tracking(self):
        m = Metrics()
        m.record_energy(5.5)
        m.record_energy(3.2)
        assert m.energy_consumed == pytest.approx(8.7, rel=1e-3)

    def test_context_switches(self):
        m = Metrics()
        m.record_context_switch()
        m.record_context_switch()
        assert m.context_switches == 2

    def test_to_dict_keys(self):
        m = Metrics()
        d = m.to_dict()
        required_keys = [
            "scheduler", "simulation_steps", "tasks_completed",
            "deadline_miss_rate", "cpu_utilization", "throughput",
            "context_switches", "total_faults", "energy_consumed",
        ]
        for key in required_keys:
            assert key in d, f"Missing key in to_dict(): {key}"

    def test_fault_breakdown(self):
        m = Metrics()
        m.record_fault({"fault_type": "RESOURCE_FAILURE", "task_id": 1, "time": 1})
        m.record_fault({"fault_type": "RESOURCE_FAILURE", "task_id": 2, "time": 2})
        m.record_fault({"fault_type": "DEADLINE_MISS",    "task_id": 3, "time": 3})
        assert m.fault_counts["RESOURCE_FAILURE"] == 2
        assert m.fault_counts["DEADLINE_MISS"] == 1


class TestMetricsResourceStats:
    def test_total_faults_matches_sum(self):
        m = Metrics()
        m.record_fault({"fault_type": "A", "task_id": 1, "time": 1})
        m.record_fault({"fault_type": "B", "task_id": 2, "time": 2})
        m.record_fault({"fault_type": "A", "task_id": 3, "time": 3})
        assert len(m.faults) == 3
        assert sum(m.fault_counts.values()) == 3
