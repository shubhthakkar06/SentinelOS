from sentinel_os.scheduler.scheduler_base import SchedulerBase
from sentinel_os.core.task import TaskState

class PriorityScheduler(SchedulerBase):
    """
    Static Priority scheduler with specialized state queues.

    Uses `effective_priority` so Priority Inheritance Protocol boosts
    are respected — a lock holder's inherited priority is visible here.
    """

    def __init__(self):
        super().__init__()

    def add_task(self, task):
        """Add a task and compute initial AI importance boost."""
        task.waiting_time = 0
        
        # CHEAP AI ADVISOR: Run once on entry and cache
        if self.ai_advisor:
            boost = self.ai_advisor.get_advisory_signal(task, {})
            task.ai_boost = boost
            task.effective_priority = task.base_priority + boost
            
        self.requeue(task)

    def get_next_task(self, system_state=None):
        """Pick the highest priority task from the READY queue only."""
        if not self.ready_queue:
            return None

        # Sort: critical tasks first, then by effective_priority (descending),
        # then by energy usage ascending (prefer low-energy tasks as tie-break)
        self.ready_queue.sort(
            key=lambda t: (
                not t.critical,
                -t.effective_priority,
                t.energy_usage,
            )
        )

        task = self.ready_queue.pop(0)
        task.waiting_time = 0
        
        # increase aging for other READY tasks
        for t in self.ready_queue:
            t.waiting_time += 1
            
        return task

    def requeue(self, task):
        """Move task to the correct collection based on its state."""
        self.remove_task(task)
        
        if task.state == TaskState.READY:
            self.ready_queue.append(task)
        elif task.state == TaskState.WAITING:
            self.wait_queue.append(task)
        elif task.state == TaskState.BLOCKED:
            self.blocked_queue.append(task)
        elif task.state == TaskState.SUSPENDED:
            self.suspended_queue.append(task)