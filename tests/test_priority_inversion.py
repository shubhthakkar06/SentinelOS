"""
tests/test_priority_inversion.py
----------------------------------
Demonstrates priority inversion and verifies that the
Priority Inheritance Protocol (PIP) resolves it.

This is the most interview-impressive test in the suite:
it shows you understand a real RTOS failure mode, can reproduce
it deterministically, and have implemented the fix.

─── Scenario ─────────────────────────────────────────────────────────
  LOW  priority=1  holds "sensor_bus" lock
  HIGH priority=9  needs "sensor_bus" → blocks on LOW
  MED  priority=5  (no lock dependency)

Without PIP:
  LOW runs at priority 1, MED (priority 5) preempts it.
  HIGH starves while MED runs — inversion!

With PIP:
  LOW inherits HIGH's priority (9), MED cannot preempt LOW.
  LOW finishes, releases lock, HIGH runs. No inversion.
"""

import pytest
from sentinel_os.core.task import Task, TaskState
from sentinel_os.components.lock_manager import LockManager

LOCK_NAME = "sensor_bus"


def make_task(tid, priority, task_type="Navigation"):
    t = Task(tid, task_type, priority, deadline=100, burst_time=10)
    t.state = TaskState.READY
    return t


class TestPriorityInversionDetection:
    """Verify the LockManager detects when inversion would occur."""

    def test_inversion_detected_on_acquire(self):
        mgr = LockManager()
        low  = make_task(1, priority=1)
        high = make_task(3, priority=9)

        # LOW acquires the lock
        assert mgr.acquire(low, LOCK_NAME) is True
        assert low.held_lock == LOCK_NAME

        # HIGH tries to acquire — blocked; PIP should boost LOW
        acquired = mgr.acquire(high, LOCK_NAME)
        assert acquired is False, "HIGH should be blocked (lock held by LOW)"
        assert mgr.inversion_events >= 1, "At least one priority inversion must be recorded"

    def test_pip_boosts_holder_to_waiter_priority(self):
        mgr = LockManager()
        low  = make_task(1, priority=1)
        high = make_task(3, priority=9)

        mgr.acquire(low, LOCK_NAME)
        mgr.acquire(high, LOCK_NAME)   # blocked; PIP fires

        # LOW's effective priority should now equal HIGH's
        assert low.effective_priority == 9, (
            f"PIP must boost lock holder to waiter's priority. "
            f"Got {low.effective_priority}, expected 9"
        )

    def test_original_priority_restored_after_release(self):
        mgr = LockManager()
        low  = make_task(1, priority=1)
        high = make_task(3, priority=9)

        mgr.acquire(low, LOCK_NAME)
        mgr.acquire(high, LOCK_NAME)   # PIP fires, low gets priority 9

        next_owner = mgr.release(low, LOCK_NAME)

        # LOW's priority is restored to base
        assert low.effective_priority == 1, (
            f"After releasing the lock, LOW's priority must revert to base (1). "
            f"Got {low.effective_priority}"
        )

    def test_lock_transferred_to_highest_priority_waiter(self):
        mgr = LockManager()
        low = make_task(1, priority=1)
        med = make_task(2, priority=5)
        high = make_task(3, priority=9)

        mgr.acquire(low, LOCK_NAME)
        mgr.acquire(med, LOCK_NAME)    # blocked
        mgr.acquire(high, LOCK_NAME)   # blocked, highest priority waiter

        next_owner = mgr.release(low, LOCK_NAME)

        # HIGH should get the lock, not MED
        assert next_owner is not None
        assert next_owner.tid == high.tid, (
            "Lock must be transferred to the HIGHEST-priority waiter"
        )
        assert next_owner.held_lock == LOCK_NAME


class TestPriorityInversionFullScenario:
    """
    End-to-end scenario: LOW holds lock, MED cannot preempt LOW
    because LOW has inherited HIGH's priority via PIP.
    """

    def test_pip_prevents_medium_from_preempting_boosted_low(self):
        from sentinel_os.scheduler.scheduler_factory import get_scheduler

        mgr = LockManager()
        sched = get_scheduler("priority")

        low  = make_task(1, priority=1)
        med  = make_task(2, priority=5)
        high = make_task(3, priority=9)

        # Setup: LOW holds lock, HIGH is blocked waiting
        mgr.acquire(low, LOCK_NAME)
        blocked = mgr.acquire(high, LOCK_NAME)
        assert blocked is False
        # Now LOW has effective_priority == 9 (inherited from HIGH)

        # Add LOW and MED to scheduler
        low.state = TaskState.READY
        med.state = TaskState.READY
        # (HIGH is BLOCKED, not in ready queue)

        sched.add_task(low)
        sched.add_task(med)

        # With PIP, LOW (effective_priority=9) should run before MED (priority=5)
        chosen = sched.get_next_task()
        assert chosen.tid == low.tid, (
            "With PIP, LOW (boosted to priority 9) must run before MED (priority 5). "
            "Without PIP, MED would preempt LOW → priority inversion!"
        )


class TestDeadlockDetection:
    def test_no_deadlock_in_simple_scenario(self):
        mgr = LockManager()
        t1 = make_task(10, priority=5)
        t2 = make_task(11, priority=3)
        mgr.acquire(t1, "lock_a")
        mgr.acquire(t2, "lock_b")
        # t2 waits on lock_a (held by t1)
        mgr.acquire(t2, "lock_a")
        # No cycle: t1 is not waiting for anything
        assert mgr.is_deadlocked() is False

    def test_pip_stats_tracked(self):
        mgr = LockManager()
        low  = make_task(1, priority=1)
        high = make_task(2, priority=8)
        mgr.acquire(low, "shared_mem")
        mgr.acquire(high, "shared_mem")

        stats = mgr.stats()
        assert stats["priority_inversion_events"] >= 1
        assert stats["priority_inheritance_boosts"] >= 1
