from base.scheduler_base import SchedulerBase

class PriorityScheduler(SchedulerBase):
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def get_next_task(self):
        if not self.tasks:
            return None

        self.tasks.sort(
            key=lambda t: (
                not t.critical,
                -t.base_priority,
                t.energy_usage
            )
        )

        return self.tasks.pop(0)

    def requeue(self, task):
        if task.state != "FAULT":
            self.tasks.append(task)