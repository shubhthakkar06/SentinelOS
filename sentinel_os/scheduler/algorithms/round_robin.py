from collections import deque
from sentinel_os.scheduler.scheduler_base import SchedulerBase
from sentinel_os.core.task import TaskState

class RoundRobin(SchedulerBase):
    """
    Round-Robin scheduler with specialized state queues.
    Fairness benchmark: every task gets equal CPU time regardless
    of priority.
    """

    def __init__(self, time_quantum: int = 2):
        super().__init__()
        self.time_quantum = time_quantum
        # We'll use self.ready_queue as a list but treat it like a deque for RR
        # (Though we could change self.ready_queue to a deque in the base class,
        # but for consistency with other schedulers we'll keep it as a list and use pop(0)).

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
        """Pick the next task in rotation from the READY queue."""
        if not self.ready_queue:
            return None
            
        task = self.ready_queue.pop(0)
        
        # increment waiting for all other READY tasks
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