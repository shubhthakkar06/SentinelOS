from sentinel_os.scheduler.scheduler_base import SchedulerBase
from sentinel_os.core.task import TaskState

class EDFScheduler(SchedulerBase):
    """
    Earliest Deadline First scheduler with specialized state queues.
    Tasks with the closest deadline run first.
    When deadlines are equal, effective_priority breaks ties (supports PIP).
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
        """Pick the task with earliest deadline from READY queue."""
        if not self.ready_queue:
            return None

        self.ready_queue.sort(
            key=lambda t: (
                t.deadline if t.deadline else float('inf'),
                -t.effective_priority,   # tie-break: higher priority first
            )
        )

        task = self.ready_queue.pop(0)
        
        # increment waiting time for remaining READY tasks
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