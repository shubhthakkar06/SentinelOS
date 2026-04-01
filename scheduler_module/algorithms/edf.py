from base.scheduler_base import SchedulerBase

class EDFScheduler(SchedulerBase):
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def get_next_task(self):
        if not self.tasks:
            return None

        self.tasks.sort(
            key=lambda t: t.deadline if t.deadline else float('inf')
        )

        return self.tasks.pop(0)

    def requeue(self, task):
        if task.state != "FAULT":
            self.tasks.append(task)