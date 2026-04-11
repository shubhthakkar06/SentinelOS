from collections import deque
from sentinel_os.scheduler.scheduler_base import SchedulerBase

class RoundRobin(SchedulerBase):
    def __init__(self, time_quantum=2):
        self.queue = deque()
        self.time_quantum = time_quantum

    def add_task(self, task):
        self.queue.append(task)

    def get_next_task(self):
        if self.queue:
            return self.queue.popleft()
        return None

    def requeue(self, task):
        if task.state != "FAULT":
            self.queue.append(task)