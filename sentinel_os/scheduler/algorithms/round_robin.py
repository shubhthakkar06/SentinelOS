from collections import deque
from sentinel_os.scheduler.scheduler_base import SchedulerBase


class RoundRobin(SchedulerBase):
    """
    Round-Robin scheduler with a fixed time quantum.

    Fairness benchmark: every task gets equal CPU time regardless
    of priority. Used as the baseline in scheduler comparisons.
    """

    def __init__(self, time_quantum: int = 2):
        super().__init__()
        self.queue: deque = deque()
        self.time_quantum = time_quantum

    def add_task(self, task):
        task.waiting_time = 0
        self.queue.append(task)

    def get_next_task(self, system_state=None):
        if not self.queue:
            return None
        task = self.queue.popleft()
        # increment waiting for all others
        for t in self.queue:
            t.waiting_time += 1
        return task

    def get_queued_tasks(self):
        return list(self.queue)

    def requeue(self, task):
        from sentinel_os.core.task import TaskState
        if task.state not in (str(TaskState.TERMINATED), "TERMINATED"):
            self.queue.append(task)