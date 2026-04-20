class SchedulerBase:
    def __init__(self):
        self.ai_advisor = None

    def set_ai_advisor(self, advisor):
        self.ai_advisor = advisor

    def add_task(self, task):
        raise NotImplementedError

    def get_next_task(self, system_state=None):
        raise NotImplementedError

    def get_queued_tasks(self):
        """Return a list of all tasks currently in the scheduler's queue."""
        raise NotImplementedError

    def requeue(self, task):
        raise NotImplementedError