"""
sentinel_os/components/lock_manager.py
----------------------------------------
Priority Inheritance Mutex for SentinelOS.

Demonstrates and solves the Priority Inversion problem — one of the
most important concepts in real-time operating systems (and a classic
interview question).

─── What is Priority Inversion? ──────────────────────────────────────
  A high-priority task (H) needs a resource held by a low-priority
  task (L). Because H is blocked, medium-priority tasks (M) preempt L
  (since L is now low-priority and M is higher). H starves while M
  runs — the system behaves as if H has *lower* priority than M.

  Real example: Mars Pathfinder 1997 — a high-priority meteorological
  task was continually preempted because of priority inversion on a
  shared bus mutex.

─── Solution: Priority Inheritance Protocol ──────────────────────────
  When L holds a lock that H is waiting on, L temporarily *inherits*
  H's priority. Now M cannot preempt L, L finishes quickly, releases
  the lock, and H runs.

  This module implements that protocol:
    - acquire(task, lock_name) → blocks if held, or grants
    - release(task, lock_name) → restores original priority, unblocks waiters
    - The HybridScheduler reads task.effective_priority which reflects inheritance
"""

from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel_os.core.task import Task


class Mutex:
    """A named mutex with priority-inheritance support."""

    def __init__(self, name: str):
        self.name = name
        self.holder: Optional["Task"] = None
        self.wait_queue: List["Task"] = []   # tasks blocked on this lock

    @property
    def is_locked(self) -> bool:
        return self.holder is not None

    def __repr__(self) -> str:
        holder_id = self.holder.tid if self.holder else "None"
        waiters = [t.tid for t in self.wait_queue]
        return f"Mutex({self.name}, holder={holder_id}, waiters={waiters})"


class LockManager:
    """
    Manages all named mutexes in the system and enforces the
    Priority Inheritance Protocol (PIP).

    Usage (by the simulator):
        acquired = lock_mgr.acquire(task, "sensor_bus")
        if not acquired:
            task.block()   # caller must handle blocking

        # ... later, when done ...
        next_task = lock_mgr.release(task, "sensor_bus")
        if next_task:
            next_task.ready()   # unblock the highest-priority waiter
    """

    def __init__(self):
        self._locks: Dict[str, Mutex] = {}
        self.inversion_events: int = 0   # total priority inversions detected
        self.inheritance_boosts: int = 0  # total times PIP was applied

    def _get_or_create(self, name: str) -> Mutex:
        if name not in self._locks:
            self._locks[name] = Mutex(name)
        return self._locks[name]

    # ------------------------------------------------------------------ #
    #  Acquire                                                             #
    # ------------------------------------------------------------------ #

    def acquire(self, task: "Task", lock_name: str) -> bool:
        """
        Attempt to acquire `lock_name` for `task`.

        Returns:
            True  — lock granted, task may proceed.
            False — lock is held by another task; task should be BLOCKED.
                    Priority Inheritance is applied automatically.
        """
        mutex = self._get_or_create(lock_name)

        if not mutex.is_locked:
            # Lock is free — grant immediately
            mutex.holder = task
            task.held_lock = lock_name
            task.waiting_for_lock = None
            return True

        # Lock is held by someone else
        holder = mutex.holder
        task.waiting_for_lock = lock_name

        # ----- Priority Inheritance Protocol -----------------------------
        # If the waiter has strictly higher effective priority than the
        # holder, boost the holder to prevent priority inversion.
        if task.effective_priority > holder.effective_priority:
            self.inversion_events += 1
            self.inheritance_boosts += 1
            original = holder.effective_priority
            holder.effective_priority = task.effective_priority
            # Note: holder.base_priority is NOT changed — only effective.

        # Add to wait queue, sorted descending by effective_priority
        mutex.wait_queue.append(task)
        mutex.wait_queue.sort(key=lambda t: t.effective_priority, reverse=True)

        return False

    # ------------------------------------------------------------------ #
    #  Release                                                             #
    # ------------------------------------------------------------------ #

    def release(self, task: "Task", lock_name: str) -> Optional["Task"]:
        """
        Release `lock_name` held by `task`.

        Steps:
          1. Restore task's original (base) priority (undo PIP boost).
          2. Grant the lock to the highest-priority waiter.
          3. Return that waiter so the caller can mark it READY.

        Returns the next task that receives the lock (or None if no waiters).
        """
        mutex = self._locks.get(lock_name)
        if mutex is None or mutex.holder is not task:
            return None

        # Step 1: restore original priority
        task.effective_priority = task.base_priority
        task.held_lock = None
        mutex.holder = None

        # Step 2: grant to highest-priority waiter
        if mutex.wait_queue:
            next_task = mutex.wait_queue.pop(0)   # already sorted by priority
            next_task.waiting_for_lock = None
            mutex.holder = next_task
            next_task.held_lock = lock_name

            # Step 3: re-apply PIP for the new holder if there are still waiters
            if mutex.wait_queue:
                top_waiter = mutex.wait_queue[0]
                if top_waiter.effective_priority > next_task.effective_priority:
                    next_task.effective_priority = top_waiter.effective_priority
                    self.inheritance_boosts += 1

            return next_task

        return None

    # ------------------------------------------------------------------ #
    #  Diagnostics                                                         #
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        return {
            "total_locks": len(self._locks),
            "priority_inversion_events": self.inversion_events,
            "priority_inheritance_boosts": self.inheritance_boosts,
            "locks": {name: repr(m) for name, m in self._locks.items()},
        }

    def is_deadlocked(self) -> bool:
        """
        Simple deadlock detection: look for a cycle in the wait-for graph.
        Task A waits for lock held by B, B waits for lock held by A → deadlock.

        For a microkernel with bounded lock depth this covers most cases.
        """
        # Build: task_id → task_id_of_holder_of_waited_lock
        wait_for: Dict[int, int] = {}
        for mutex in self._locks.values():
            if mutex.holder:
                for waiter in mutex.wait_queue:
                    wait_for[waiter.tid] = mutex.holder.tid

        # DFS cycle detection
        visited: set = set()
        rec_stack: set = set()

        def has_cycle(node_id: int) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            neighbor = wait_for.get(node_id)
            if neighbor is not None:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for tid in list(wait_for.keys()):
            if tid not in visited:
                if has_cycle(tid):
                    return True
        return False
