from sentinel_os.scheduler.scheduler_factory import get_scheduler
from sentinel_os.scheduler.scheduler_base import SchedulerBase

class Kernel:
    def __init__(self, policy="hybrid", ai_advisor=None):
        self.policy = policy
        self.scheduler = get_scheduler(policy)
        if ai_advisor:
            self.scheduler.set_ai_advisor(ai_advisor)

    def add_tasks(self, tasks):
        for task in tasks:
            self.scheduler.add_task(task)

    def get_next_task(self, system_state=None):
        return self.scheduler.get_next_task(system_state)

    def requeue_task(self, task):
        self.scheduler.requeue(task)