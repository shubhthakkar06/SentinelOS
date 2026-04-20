"""
tests/test_scheduler.py
------------------------
Deterministic correctness tests for all four scheduling algorithms.

These are REAL tests with assertions — not print loops.
Each test uses a fixed task set so failures are reproducible.
"""

import pytest
from sentinel_os.core.task import Task, TaskState
from sentinel_os.scheduler.scheduler_factory import get_scheduler


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def make_task(tid, priority=5, deadline=None, critical=False, task_type="Navigation"):
    """Create a task with deterministic burst_time so tests don't rely on random."""
    t = Task(tid, task_type, priority, deadline=deadline, critical=critical, burst_time=10)
    t.state = TaskState.READY
    return t


# ------------------------------------------------------------------ #
#  EDF Scheduler                                                       #
# ------------------------------------------------------------------ #

class TestEDFScheduler:
    def test_earliest_deadline_selected_first(self):
        sched = get_scheduler("edf")
        t1 = make_task(1, deadline=50)
        t2 = make_task(2, deadline=20)    # earliest
        t3 = make_task(3, deadline=35)
        for t in [t1, t2, t3]:
            sched.add_task(t)

        chosen = sched.get_next_task()
        assert chosen.tid == 2, "EDF must pick the task with the earliest deadline"

    def test_no_deadline_tasks_go_last(self):
        sched = get_scheduler("edf")
        t_no_dl  = make_task(10, deadline=None)
        t_has_dl = make_task(11, deadline=5)
        sched.add_task(t_no_dl)
        sched.add_task(t_has_dl)

        first = sched.get_next_task()
        assert first.tid == 11, "Task with a deadline should run before no-deadline task"

    def test_empty_returns_none(self):
        sched = get_scheduler("edf")
        assert sched.get_next_task() is None

    def test_requeue_does_not_requeue_terminated(self):
        sched = get_scheduler("edf")
        t = make_task(1)
        t.state = TaskState.TERMINATED
        sched.add_task(t)
        sched.get_next_task()   # remove it
        sched.requeue(t)        # should be ignored
        assert sched.get_next_task() is None


# ------------------------------------------------------------------ #
#  Priority Scheduler                                                  #
# ------------------------------------------------------------------ #

class TestPriorityScheduler:
    def test_highest_priority_first(self):
        sched = get_scheduler("priority")
        t_low  = make_task(1, priority=2)
        t_high = make_task(2, priority=9)
        t_mid  = make_task(3, priority=5)
        for t in [t_low, t_high, t_mid]:
            sched.add_task(t)

        chosen = sched.get_next_task()
        assert chosen.tid == 2, "Priority scheduler must pick highest priority task"

    def test_critical_task_beats_higher_numeric_priority(self):
        sched = get_scheduler("priority")
        t_norm     = make_task(1, priority=10, critical=False)
        t_critical = make_task(2, priority=3,  critical=True)
        sched.add_task(t_norm)
        sched.add_task(t_critical)

        chosen = sched.get_next_task()
        assert chosen.tid == 2, "Critical tasks must be scheduled before non-critical regardless of priority"

    def test_effective_priority_used(self):
        """Priority inheritance: boosted task should run before its base-priority peer."""
        sched = get_scheduler("priority")
        t_base    = make_task(1, priority=5)    # base priority 5
        t_boosted = make_task(2, priority=3)    # base priority 3, but boosted
        t_boosted.effective_priority = 8        # simulate PIP boost

        sched.add_task(t_base)
        sched.add_task(t_boosted)

        chosen = sched.get_next_task()
        assert chosen.tid == 2, "Effective priority (PIP boost) must override base priority"


# ------------------------------------------------------------------ #
#  Round Robin Scheduler                                               #
# ------------------------------------------------------------------ #

class TestRoundRobin:
    def test_fifo_order(self):
        sched = get_scheduler("rr")
        t1 = make_task(1)
        t2 = make_task(2)
        t3 = make_task(3)
        for t in [t1, t2, t3]:
            sched.add_task(t)

        order = [sched.get_next_task().tid for _ in range(3)]
        assert order == [1, 2, 3], "Round Robin must dispatch tasks in FIFO order"

    def test_requeue_appends_to_back(self):
        sched = get_scheduler("rr")
        t1 = make_task(1)
        t2 = make_task(2)
        sched.add_task(t1)
        sched.add_task(t2)

        first = sched.get_next_task()        # pops t1
        first.state = TaskState.READY
        sched.requeue(first)                 # t1 goes to back: [t2, t1]

        second = sched.get_next_task()
        assert second.tid == 2, "After requeue, t2 should run before re-enqueued t1"

    def test_empty_returns_none(self):
        sched = get_scheduler("rr")
        assert sched.get_next_task() is None


# ------------------------------------------------------------------ #
#  Hybrid Scheduler                                                    #
# ------------------------------------------------------------------ #

class TestHybridScheduler:
    def test_critical_task_beats_non_critical_equal_deadline(self):
        """Critical flag gives +50 score; a non-critical task with the same deadline loses."""
        sched = get_scheduler("hybrid")
        # Both have same far deadline → deadline_score = 0; critical wins via +50
        t_norm  = make_task(1, priority=5, deadline=200, critical=False)
        t_crit  = make_task(2, priority=1, critical=True, deadline=200)
        sched.add_task(t_norm)
        sched.add_task(t_crit)

        chosen = sched.get_next_task()
        assert chosen.tid == 2, (
            "When deadlines are equal, critical task's +50 bonus must win"
        )

    def test_aging_prevents_starvation(self):
        """A low-priority task gains priority over time via aging."""
        sched = get_scheduler("hybrid")
        t_low  = make_task(1, priority=1)
        t_high = make_task(2, priority=8)
        sched.add_task(t_low)
        sched.add_task(t_high)

        # Simulate t_low waiting for many ticks
        t_low.waiting_time = 100   # massive aging score

        chosen = sched.get_next_task()
        assert chosen.tid == 1, "Starvation prevention: highly aged low-priority task should win"

    def test_execution_penalty_reduces_frequency(self):
        """A task that has run many times gets penalised to give others a turn."""
        sched = get_scheduler("hybrid")
        t_overrun = make_task(1, priority=5)
        t_fresh   = make_task(2, priority=5)
        sched.add_task(t_overrun)
        sched.add_task(t_fresh)

        # Mark t_overrun as having run many times
        sched.execution_count[1] = 10

        chosen = sched.get_next_task()
        assert chosen.tid == 2, "Overrun task should be penalised in favour of fresher task"

    def test_empty_returns_none(self):
        sched = get_scheduler("hybrid")
        assert sched.get_next_task() is None

    def test_requeue_terminated_task_not_readded(self):
        sched = get_scheduler("hybrid")
        t = make_task(1)
        sched.add_task(t)
        sched.get_next_task()   # remove
        t.state = TaskState.TERMINATED
        sched.requeue(t)
        assert sched.get_next_task() is None