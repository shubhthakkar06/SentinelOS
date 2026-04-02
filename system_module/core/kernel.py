from scheduler_module.scheduler_factory import get_scheduler
from scheduler_module.base.scheduler_base import SchedulerBase

class Kernel:
    def __init__(self, policy="hybrid"):
        self.policy = policy
        self.scheduler = get_scheduler(policy)

    def add_tasks(self, tasks):
        for task in tasks:
            self.scheduler.add_task(task)

    def get_next_task(self):
        return self.scheduler.get_next_task()

    def requeue_task(self, task):
        self.scheduler.requeue(task)