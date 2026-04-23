from sentinel_os.scheduler.scheduler_base import SchedulerBase
from sentinel_os.core.task import TaskState

class HybridScheduler(SchedulerBase):
    def __init__(self):
        super().__init__()
        self.execution_count = {}   # track how many times each task ran

    def add_task(self, task):
        """Add a task to the system and immediately compute AI advice."""
        task.waiting_time = 0
        self.execution_count[task.tid] = self.execution_count.get(task.tid, 0)
        
        # CHEAP AI ADVISOR: Run once on entry and cache
        if self.ai_advisor:
            # Note: system_state is None here during initial entry, we'll re-run if needed
            # but for now we set baseline advice.
            boost = self.ai_advisor.get_advisory_signal(task, {})
            task.ai_boost = boost
            task.effective_priority = task.base_priority + boost
            
        self.requeue(task)

    def compute_score(self, task):
        """Compute scheduling score for a READY task. AI advice is now cached."""
        deadline = task.deadline if task.deadline else 100

        # normalize values
        critical_score = 50 if task.critical else 0
        priority_score = task.effective_priority * 5   # respecting inherited/AI priority
        aging_score = task.waiting_time * 10
        deadline_score = max(0, 50 - deadline)
        execution_penalty = self.execution_count.get(task.tid, 0) * 15

        # AI boost is retrieved from cache, not recalculated
        ai_boost_score = task.ai_boost * 10
            
        # FINAL SCORE
        score = (
            critical_score +
            priority_score +
            aging_score +
            deadline_score +
            ai_boost_score -
            execution_penalty
        )

        return -score   # higher score = higher priority

    def get_next_task(self, system_state=None):
        """Pick the best task from the READY queue only."""
        if not self.ready_queue:
            return None

        # Sort only the actionable READY tasks
        self.ready_queue.sort(key=self.compute_score)

        task = self.ready_queue.pop(0)

        # update execution history
        self.execution_count[task.tid] += 1
        task.waiting_time = 0

        # increase aging for other READY tasks
        for t in self.ready_queue:
            t.waiting_time += 1

        return task

    def requeue(self, task):
        """Move task to the correct collection based on its state."""
        # Ensure it's not in any queue first
        self.remove_task(task)
        
        if task.state == TaskState.READY:
            self.ready_queue.append(task)
        elif task.state == TaskState.WAITING:
            self.wait_queue.append(task)
        elif task.state == TaskState.BLOCKED:
            self.blocked_queue.append(task)
        elif task.state == TaskState.SUSPENDED:
            self.suspended_queue.append(task)
        # TERMINATED tasks are not requeued