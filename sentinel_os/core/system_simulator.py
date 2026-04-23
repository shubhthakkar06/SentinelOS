from __future__ import annotations

"""
sentinel_os/core/system_simulator.py
--------------------------------------
Main simulation engine for SentinelOS AUV.

Drives the full operating system simulation including:
  - 7-state process management (NEW→READY→RUNNING→BLOCKED/WAITING/SUSPENDED→FAULT→TERMINATED)
  - Realistic battery management (BMS with cell-level tracking)
  - Underwater environment simulation (depth, heading, pressure)
  - Multi-phase survival mode with cascading degradation
  - Physics-informed fault injection
  - AI advisory system
  - Priority inheritance / lock management
"""

import random
from typing import Optional

from sentinel_os.components.resource_manager import ResourceManager
from sentinel_os.components.event_manager import EventManager
from sentinel_os.components.lock_manager import LockManager
from sentinel_os.components.environment import UnderwaterEnvironment
from sentinel_os.core.kernel import Kernel
from sentinel_os.components.task_generator import TaskGenerator
from sentinel_os.components.fault_injector import FaultInjector
from sentinel_os.monitoring.metrics import Metrics
from sentinel_os.monitoring.logger import Logger
from sentinel_os.core.context_switch import ContextSwitch
from sentinel_os.monitoring.dataset_generator import DatasetGenerator
from sentinel_os.ai.ai_advisor import AIAdvisor
from sentinel_os.core.task import TaskState, PERSISTENT_TASKS


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
        Random seed for reproducibility.
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
        self.resource_manager = ResourceManager()
        self.kernel = Kernel(
            policy=scheduler_policy, 
            ai_advisor=self.ai_advisor,
            resource_manager=self.resource_manager
        )
        self.task_generator = TaskGenerator()
        self.fault_injector = FaultInjector()
        self.event_manager = EventManager()
        self.lock_manager = LockManager() if enable_locks else None
        self.environment = UnderwaterEnvironment()

        self.metrics = Metrics()
        self.metrics.scheduler_name = scheduler_policy

        self.logger = Logger(verbose=verbose)
        self.dataset_generator = DatasetGenerator()
        self.context_switch = ContextSwitch()

        self.prev_task = None

        # Survival phase tracking (for logging phase transitions)
        self._last_survival_phase = 0

        # Phase transition messages
        self._phase_messages = {
            1: "⚠ PHASE 1: LINK LOST — GPS intermittent, auto-navigation engaged",
            2: "⚠ PHASE 2: POWER CONSERVATION — Non-critical processes suspended, throttle limited",
            3: "🔴 PHASE 3: CRITICAL OPERATIONS — Only essential systems active",
            4: "🚨 PHASE 4: EMERGENCY ASCENT — Auto-surface initiated, distress beacon active",
            5: "💀 PHASE 5: DEAD SHIP — All systems halted, blackbox recording only",
        }

    # ------------------------------------------------------------------ #

    def initialize(self):
        self.logger.log("=" * 50)
        self.logger.log(f"  SentinelOS Initializing — scheduler: {self.metrics.scheduler_name}")
        
        # BOOT PHASE: Initialize persistent services
        self.logger.log("  [BOOT] Starting core vehicle services...")
        initial_services = self.task_generator.initialize_services()
        for s in initial_services:
            s.state = TaskState.READY  # Must be READY to be schedulable
            self.resource_manager.allocate(s)
            self.logger.log(f"    - {s.task_type} service ONLINE")
            
        self.kernel.add_tasks(initial_services)
            
        self.logger.log(f"  Battery: {self.resource_manager.bms.pack_soc:.0f}% | Cells: {self.resource_manager.bms.healthy_cell_count}/8")
        self.logger.log(f"  Depth: {self.environment.depth:.0f}m | Heading: {self.environment.heading:.0f}°")
        self.logger.log("=" * 50)

    def run(self) -> dict:
        """Run the simulation. Returns a results dict with all KPIs."""
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
        """Return all tasks currently in the system."""
        return self.kernel.scheduler.get_queued_tasks()

    # ------------------------------------------------------------------ #
    #  Per-tick logic                                                      #
    # ------------------------------------------------------------------ #

    def step(self):
        """Execute a single simulation tick."""
        # --- Update environment ---
        self.environment.tick()

        # --- Battery Guard ---
        if self.resource_manager.bms.pack_soc <= 0:
            self.logger.error("SYSTEM HALTED: TOTAL POWER FAILURE.")
            return

        # --- Survival phase check ---
        if self.resource_manager.mission_mode == "Survival":
            old_phase = self._last_survival_phase
            new_phase = self.resource_manager.update_survival_phase()
            if new_phase != old_phase:
                msg = self._phase_messages.get(new_phase, f"Phase {new_phase}")
                self.logger.log(msg, level="WARNING")
                self._apply_survival_phase(new_phase)
                self._last_survival_phase = new_phase

            # Auto-surface in phase 4
            if new_phase >= 4:
                self.environment.set_surface()
                self.environment.set_throttle(100)

        # 1. Generate environment events
        self.event_manager.generate_events(self.time)
        events = self.event_manager.get_events()
        for e in events:
            self.logger.log(f"  Event: {e['type']} @ t={e['time']}")

        # 2. Get env snapshot for system state
        env_data = self.environment.snapshot()

        # 3. Generate new transient tasks (Jobs)
        system_state = self.resource_manager.system_state_snapshot(self.time, env_data)
        new_tasks = self.task_generator.generate_task(self.time, system_state)
        for task in new_tasks:
            task.arrival_time = self.time
            task.state = TaskState.READY
            self.metrics.record_task_arrival(task.tid, self.time)
            
        # Admission Control check via Kernel
        admitted, rejected = self.kernel.add_tasks(new_tasks)
        
        if admitted:
            types = ", ".join(t.task_type for t in admitted)
            self.logger.log(f"  +{len(admitted)} task(s) admitted: {types}")
            
        for task, reason in rejected:
            self.logger.log(f"  ! ADMISSION REJECTED: {task.task_type} — {reason}", level="WARNING")

        # 4. Process I/O waiting tasks
        self._tick_waiting_tasks()

        # 5. Pick next task
        task = self.kernel.get_next_task(system_state)

        # 6. Context switch
        if task != self.prev_task and (task is not None or self.prev_task is not None):
            self.context_switch.switch(self.prev_task, task)
            self.metrics.record_context_switch()

        # 7. Execute task
        if task:
            # 7a. Attempt lock acquisition
            lock_acquired = True
            if self.lock_manager and task.waiting_for_lock:
                lock_acquired = self.lock_manager.acquire(task, task.waiting_for_lock)
                if not lock_acquired:
                    task.block(reason="LOCK")
                    self.logger.log(f"  Task {task.tid} ({task.task_type}) BLOCKED on lock '{task.waiting_for_lock}'")
                    self.kernel.requeue_task(task)
                    self._record_idle_step(events)
                    self.prev_task = None
                    self.time += 1
                    return

            # 7b. Allocate memory
            if not self.resource_manager.allocate(task):
                self.logger.log(f"  Task {task.tid} ({task.task_type}) BLOCKED — memory unavailable "
                                f"({self.resource_manager.pressure.value} pressure)")
                task.block(reason="MEM")
                self.kernel.requeue_task(task)
                self._record_idle_step(events)
                self.prev_task = task
                self.time += 1
                return

            # 7c. Mark as RUNNING and execute
            task.state = TaskState.RUNNING
            self.metrics.record_task_started(task.tid, self.time)

            task_info = {
                "task_running": True,
                "task_id": task.tid,
                "task_type": task.task_type,
                "task_state": task.state.value,
            }

            exec_time = task.execute(time_slice=2, system_state=system_state)
            energy_drain = self.resource_manager.consume_energy(
                task,
                depth=self.environment.depth,
                water_temp=self.environment.water_temperature,
            )
            self.metrics.record_energy(energy_drain)

            # 7d. Check if task entered I/O WAITING
            if task.state == TaskState.WAITING:
                self.logger.log(f"  ⏳ Task {task.tid} ({task.task_type}) → WAITING on {task.io_device}")
                self.kernel.requeue_task(task)
                self._record_step(events, task_info)
                self.prev_task = None
                self.time += 1
                return

            # 7e. AI advisor signal
            ai_boost_applied = False
            if self.ai_advisor:
                # Optimized: Only re-calculate if not already in cache or major change
                boost = self.ai_advisor.get_advisory_signal(task, system_state)
                if boost > 0:
                    ai_boost_applied = True
                    task.ai_boost = boost
                    task.effective_priority = task.base_priority + boost
                    task.intervention_outcome = "PENDING"  # Track for metrics
                    self.logger.log(f"  ⚡ AI Intervention: Boosted Task {task.tid} (priority +{boost})")
                else:
                    task.ai_boost = 0
                    task.effective_priority = task.base_priority

            # 7f. Inject system-level faults
            sys_faults = self.fault_injector.inject_task_fault(task, self.time, system_state)
            for f in sys_faults:
                self.metrics.record_fault(f)
                self.logger.log(f"  ⚡ Fault: {f['fault_type']} on Task {task.tid} ({task.task_type}) — {f.get('description', '')}")
                if f['fault_type'] == "RESOURCE_FAILURE":
                    task.fault()

            actual_fault = task.state == TaskState.FAULT or len(sys_faults) > 0

            # Evaluation of AI Intervention
            if self.ai_advisor and task.intervention_outcome == "PENDING":
                if actual_fault:
                    # AI boosted but it faulted anyway -> Accurate Prediction (of unpreventable failure)
                    self.metrics.record_ai_intervention("ACCURATE_PREDICTION")
                    task.intervention_outcome = "RESOLVED"
                elif task.remaining_time <= 1: # Nearing completion successfully
                    self.metrics.record_ai_intervention("PREVENTION_SUCCESS")
                    task.intervention_outcome = "RESOLVED"

            # Calculate recommended priority (base + boost)
            rec_prio = task.base_priority
            if self.ai_advisor:
                # We use the current AI signal as the training label for prioritization
                rec_prio = min(10, task.base_priority + self.ai_advisor.calculate_boost(self.ai_advisor.last_confidence))

            self.dataset_generator.record_sample(
                self.time, task, self.resource_manager.available_memory,
                env_data, recommended_priority=rec_prio, fault_occurred=actual_fault
            )

            # 7g. Release memory if done
            if task.state == TaskState.TERMINATED or task.remaining_time <= 0:
                self.resource_manager.release(task)
                self.prev_task = None
            else:
                self.prev_task = task

            # 7h. Release held lock
            if self.lock_manager and task.held_lock:
                next_owner = self.lock_manager.release(task, task.held_lock)
                if next_owner:
                    next_owner.state = TaskState.READY
                    self.kernel.requeue_task(next_owner)

            # 7i. Decide next state
            if task.state == TaskState.FAULT:
                recovered = task.try_recover()
                if recovered:
                    self.logger.log(f"  ↩ Task {task.tid} ({task.task_type}) recovered → READY")
                    self.kernel.requeue_task(task)
                else:
                    self.logger.log(f"  ✗ Task {task.tid} ({task.task_type}) PERMANENTLY FAILED")
                    self.metrics.record_task_fault_terminated(task.tid, self.time)
                    # Allow persistent task to respawn
                    if task.task_type in PERSISTENT_TASKS:
                        self.task_generator.mark_completed(task.task_type)

            elif task.is_done():
                task.terminate()
                missed_deadline = task.missed_deadline(self.time)
                self.logger.log(f"  ✓ Task {task.tid} ({task.task_type}) COMPLETED @ t={self.time}")
                self.metrics.record_task_completed(task.tid, self.time, missed_deadline)
                # Allow persistent task to respawn
                if task.task_type in PERSISTENT_TASKS:
                    self.task_generator.mark_completed(task.task_type)

            else:
                task.state = TaskState.READY
                self.kernel.requeue_task(task)

            self._record_step(events, task_info)

        else:
            self.logger.log(f"  CPU IDLE @ t={self.time}")
            self._record_idle_step(events)

        self.prev_task = task
        self.time += 1

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _tick_waiting_tasks(self):
        """Process tasks only in the WAITING (I/O) collection."""
        wait_queue = list(self.kernel.scheduler.wait_queue)
        for task in wait_queue:
            if task.tick_io_wait():
                task.state = TaskState.READY
                self.kernel.requeue_task(task)
                self.logger.log(f"  📡 Task {task.tid} ({task.task_type}) I/O complete on {task.io_device} → READY")

    def _apply_survival_phase(self, phase: int):
        """Apply system-level effects of survival phase transitions."""
        tasks = self.kernel.scheduler.get_queued_tasks()

        if phase >= 2:
            # Suspend non-critical tasks
            non_critical = {"Hydrophone", "DataLogging", "MissionPayload", "GPSSync"}
            for t in tasks:
                if t.task_type in non_critical and t.state != TaskState.SUSPENDED:
                    t.suspend(by="kernel")
                    self.logger.log(f"  🔒 Kernel suspended Task {t.tid} ({t.task_type}) — power conservation")

            # Throttle propulsion
            self.environment.set_throttle(min(self.environment.throttle, 50))

        if phase >= 3:
            # Only critical tasks run
            critical_types = {"Navigation", "DepthControl", "HullIntegrity",
                              "BatteryMonitor", "O2Scrubber", "ThermalRegulation"}
            for t in tasks:
                if t.task_type not in critical_types and t.state != TaskState.SUSPENDED:
                    t.suspend(by="kernel")
                    self.logger.log(f"  🔒 Kernel suspended Task {t.tid} ({t.task_type}) — critical ops only")

            # Passive sonar only
            self.environment.set_sonar("passive")

        if phase >= 4:
            # Emergency — auto surface
            self.environment.set_surface()
            self.logger.log("  🆘 AUTO-SURFACE INITIATED — Distress beacon ACTIVE")

    def suspend_task(self, tid: int) -> str:
        """Suspend a task by TID. Returns status message."""
        tasks = self.kernel.scheduler.get_queued_tasks()
        for t in tasks:
            if t.tid == tid:
                if t.state == TaskState.SUSPENDED:
                    return f"Task {tid} is already suspended."
                t.suspend(by="operator")
                return f"Task {tid} ({t.task_type}) suspended."
        return f"Task {tid} not found."

    def resume_task(self, tid: int) -> str:
        """Resume a suspended task. Returns status message."""
        tasks = self.kernel.scheduler.get_queued_tasks()
        for t in tasks:
            if t.tid == tid:
                if t.state != TaskState.SUSPENDED:
                    return f"Task {tid} is not suspended (state: {t.state.value})."
                t.resume()
                return f"Task {tid} ({t.task_type}) resumed → READY."
        return f"Task {tid} not found."

    def kill_task(self, tid: int) -> str:
        """Terminate a task by TID. Returns status message."""
        tasks = self.kernel.scheduler.get_queued_tasks()
        for t in tasks:
            if t.tid == tid:
                t.terminate()
                self.resource_manager.release(t)
                if t.task_type in PERSISTENT_TASKS:
                    self.task_generator.mark_completed(t.task_type)
                return f"Task {tid} ({t.task_type}) terminated. Memory released."
        return f"Task {tid} not found."

    def nice_task(self, tid: int, priority: int) -> str:
        """Change a task's priority. Returns status message."""
        tasks = self.kernel.scheduler.get_queued_tasks()
        for t in tasks:
            if t.tid == tid:
                old = t.base_priority
                t.base_priority = max(1, min(10, priority))
                t.effective_priority = t.base_priority
                return f"Task {tid} priority: {old} → {t.base_priority}"
        return f"Task {tid} not found."

    def _record_step(self, events, task_info):
        self.metrics.record_step({
            "time": self.time,
            "events": len(events),
            "memory": self.resource_manager.available_memory,
            "battery": self.resource_manager.current_battery,
            "depth": self.environment.depth,
            **task_info
        })

    def _record_idle_step(self, events):
        self.metrics.record_step({
            "time": self.time,
            "events": len(events),
            "memory": self.resource_manager.available_memory,
            "battery": self.resource_manager.current_battery,
            "depth": self.environment.depth,
            "task_running": False,
        })
