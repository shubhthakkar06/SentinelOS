"""
sentinel_os/core/system_simulator.py
--------------------------------------
Main simulation engine for SentinelOS.

Refactored from the original to:
  1. Use the real Task state machine (no bare random.random() faults)
  2. Feed actual system state into fault decisions
  3. Properly record all KPIs via the Metrics engine
  4. Support the LockManager for priority inversion demonstration
  5. Be seeded for reproducibility (essential for scheduler comparison)
  6. Return results dict so scripts can collect data programmatically
"""

import random
from typing import Optional

from sentinel_os.components.resource_manager import ResourceManager
from sentinel_os.components.event_manager import EventManager
from sentinel_os.components.lock_manager import LockManager
from sentinel_os.core.kernel import Kernel
from sentinel_os.components.task_generator import TaskGenerator
from sentinel_os.components.fault_injector import FaultInjector
from sentinel_os.monitoring.metrics import Metrics
from sentinel_os.monitoring.logger import Logger
from sentinel_os.core.context_switch import ContextSwitch
from sentinel_os.monitoring.dataset_generator import DatasetGenerator
from sentinel_os.ai.ai_advisor import AIAdvisor
from sentinel_os.core.task import TaskState


class SystemSimulator:
    """
    Drives a full AUV operating system simulation.

    Parameters
    ----------
    scheduler_policy : str
        One of "hybrid", "edf", "priority", "rr".
    enable_ai : bool
        Whether to load and use the AI advisor.
    seed : int | None
        Random seed for reproducibility. Required for fair scheduler comparison.
    max_time : int
        Number of simulation ticks to run.
    enable_locks : bool
        Enable the LockManager (priority inversion demonstration).
    verbose : bool
        If False, suppresses per-step log output.
    """

    def __init__(
        self,
        scheduler_policy: str = "hybrid",
        enable_ai: bool = True,
        seed: Optional[int] = None,
        max_time: int = 300,
        enable_locks: bool = True,
        verbose: bool = True,
    ):
        if seed is not None:
            random.seed(seed)

        self.time = 0
        self.max_time = max_time
        self.verbose = verbose

        self.ai_advisor = AIAdvisor() if enable_ai else None
        self.kernel = Kernel(policy=scheduler_policy, ai_advisor=self.ai_advisor)
        self.task_generator = TaskGenerator()
        self.fault_injector = FaultInjector()
        self.event_manager = EventManager()
        self.lock_manager = LockManager() if enable_locks else None
        self.resource_manager = ResourceManager()

        self.metrics = Metrics()
        self.metrics.scheduler_name = scheduler_policy

        self.logger = Logger(verbose=verbose)
        self.dataset_generator = DatasetGenerator()
        self.context_switch = ContextSwitch()

        self.prev_task = None

    # ------------------------------------------------------------------ #

    def initialize(self):
        self.logger.log("=" * 50)
        self.logger.log(f"  SentinelOS Initializing — scheduler: {self.metrics.scheduler_name}")
        self.logger.log("=" * 50)

    def run(self) -> dict:
        """
        Run the simulation. Returns a results dict with all KPIs.
        """
        self.logger.log("Simulation started.")

        while self.time < self.max_time:
            self.step()

        self.logger.log("Simulation complete.")
        return self.get_results()

    def get_results(self) -> dict:
        """Calculate and return full KPI results."""
        self.metrics.summary()
        result = self.metrics.to_dict()
        result["resource_stats"] = self.resource_manager.stats()
        if self.lock_manager:
            result["lock_stats"] = self.lock_manager.stats()
        return result

    def set_scheduler(self, policy: str):
        """Hot-swap the scheduling policy."""
        from sentinel_os.scheduler.scheduler_factory import get_scheduler
        new_scheduler = get_scheduler(policy)
        if self.ai_advisor:
            new_scheduler.set_ai_advisor(self.ai_advisor)
        
        # Migrate tasks from old scheduler to new
        old_tasks = self.kernel.scheduler.get_queued_tasks()
        self.kernel.scheduler = new_scheduler
        self.metrics.scheduler_name = policy
        
        for t in old_tasks:
            self.kernel.add_tasks([t])
        
        self.logger.log(f"  🔄 Scheduler swapped to: {policy}")

    def get_all_tasks(self):
        """Return all tasks currently in the system (Running + Queued)."""
        tasks = self.kernel.scheduler.get_queued_tasks()
        if self.prev_task and self.prev_task.state not in (TaskState.TERMINATED, "TERMINATED"):
            # If prev_task is still active (e.g. was just running but not yet requeued)
            # This is a bit tricky depending on exactly when we call this.
            # Usually, the 'running' task is the one we just picked.
            pass
        return tasks

    # ------------------------------------------------------------------ #
    #  Per-tick logic                                                      #
    # ------------------------------------------------------------------ #

    def step(self):
        """Execute a single simulation tick."""
        # --- Battery Guard ---
        if self.resource_manager.current_battery <= 0:
            self.logger.error("SYSTEM HALTED: TOTAL POWER FAILURE.")
            return
            
        # 1. Generate environment events
        self.event_manager.generate_events(self.time)
        events = self.event_manager.get_events()
        for e in events:
            self.logger.log(f"  Event: {e['type']} @ t={e['time']}")

        # 2. Generate new tasks
        new_tasks = self.task_generator.generate_task(self.time)
        for task in new_tasks:
            task.arrival_time = self.time
            task.state = TaskState.READY          # NEW → READY before queuing
            self.metrics.record_task_arrival(task.tid, self.time)
        self.kernel.add_tasks(new_tasks)
        if new_tasks:
            self.logger.log(f"  +{len(new_tasks)} task(s) arrived")

        # 3. Snapshot system state (used by fault model + AI)
        system_state = self.resource_manager.system_state_snapshot(self.time)

        # 4. Pick next task
        task = self.kernel.get_next_task(system_state)

        # 5. Context switch
        if task != self.prev_task and (task is not None or self.prev_task is not None):
            self.context_switch.switch(self.prev_task, task)
            self.metrics.record_context_switch()

        # 6. Update waiting time for all tasks NOT running
        if task:
            # 7. Attempt lock acquisition (optional)
            lock_acquired = True
            if self.lock_manager and task.waiting_for_lock:
                lock_acquired = self.lock_manager.acquire(task, task.waiting_for_lock)
                if not lock_acquired:
                    task.block(reason="LOCK")
                    self.logger.log(f"  Task {task.tid} BLOCKED on lock '{task.waiting_for_lock}'")
                    self.kernel.requeue_task(task)
                    self._record_idle_step(events)
                    self.prev_task = None
                    self.time += 1
                    return

            # 8. Allocate memory
            if not self.resource_manager.allocate(task):
                self.logger.log(f"  Task {task.tid} WAITING — memory unavailable "
                                f"({self.resource_manager.pressure.value} pressure)")
                task.block(reason="MEM")
                self.kernel.requeue_task(task)
                self._record_idle_step(events)
                self.prev_task = task
                self.time += 1
                return

            # 9. Mark as RUNNING and execute
            task.state = TaskState.RUNNING
            self.metrics.record_task_started(task.tid, self.time)

            # We store task running info for metrics record_step
            task_info = {
                "task_running": True,
                "task_id": task.tid,
                "task_type": task.task_type,
                "task_state": task.state.value,
            }

            exec_time = task.execute(time_slice=2, system_state=system_state)
            energy_drain = self.resource_manager.consume_energy(task)
            self.metrics.record_energy(energy_drain)

            # 10. AI advisor signal
            ai_boost_applied = False
            if self.ai_advisor:
                boost = self.ai_advisor.get_advisory_signal(task, system_state)
                if boost > 0:
                    ai_boost_applied = True
                    # Apply boost to effective priority
                    task.ai_boost = boost
                    task.effective_priority = task.base_priority + boost
                    self.logger.log(f"  ⚡ AI Intervention: Boosted Task {task.tid} (priority +{boost})")
                else:
                    task.ai_boost = 0
                    task.effective_priority = task.base_priority

            # 11. Inject system-level faults (Variety + Scenarios)
            sys_faults = self.fault_injector.inject_task_fault(task, self.time, system_state)
            for f in sys_faults:
                self.metrics.record_fault(f)
                self.logger.log(f"  ⚡ Fault: {f['fault_type']} on Task {task.tid}")
                if f['fault_type'] == "RESOURCE_FAILURE":
                    task.fault() # Trigger tasks internal recovery machines

            actual_fault = task.state == TaskState.FAULT or len(sys_faults) > 0
            if self.ai_advisor:
                self.metrics.record_ai_intervention(ai_boost_applied, actual_fault)

            self.dataset_generator.record_sample(
                self.time, task, self.resource_manager.available_memory,
                fault_occurred=actual_fault
            )

            # 12. Check status for memory release
            if task.state == TaskState.TERMINATED or task.remaining_time <= 0:
                self.resource_manager.release(task)
                self.prev_task = None
            else:
                self.prev_task = task

            # 14. Release held lock (if any)
            if self.lock_manager and task.held_lock:
                next_owner = self.lock_manager.release(task, task.held_lock)
                if next_owner:
                    next_owner.state = TaskState.READY
                    self.kernel.requeue_task(next_owner)

            # 15. Decide next state
            if task.state == TaskState.FAULT:
                recovered = task.try_recover()
                if recovered:
                    self.logger.log(f"  ↩ Task {task.tid} recovered → READY")
                    self.kernel.requeue_task(task)
                else:
                    self.logger.log(f"  ✗ Task {task.tid} PERMANENTLY FAILED")
                    self.metrics.record_task_fault_terminated(task.tid, self.time)

            elif task.is_done():
                task.terminate()
                missed_deadline = task.missed_deadline(self.time)
                self.logger.log(f"  ✓ Task {task.tid} COMPLETED @ t={self.time}")
                self.metrics.record_task_completed(task.tid, self.time, missed_deadline)

            else:
                task.state = TaskState.READY
                self.kernel.requeue_task(task)

            self.metrics.record_step({
                "time": self.time,
                "events": len(events),
                "memory": self.resource_manager.available_memory,
                "battery": self.resource_manager.current_battery,
                **task_info
            })

        else:
            self.logger.log(f"  CPU IDLE @ t={self.time}")
            self._record_idle_step(events)

        self.prev_task = task
        self.time += 1

    def _record_idle_step(self, events):
        self.metrics.record_step({
            "time": self.time,
            "events": len(events),
            "memory": self.resource_manager.available_memory,
            "battery": self.resource_manager.current_battery,
            "task_running": False,
        })
