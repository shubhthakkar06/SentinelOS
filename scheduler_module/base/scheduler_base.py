class SchedulerBase:
    def add_task(self, task):
        raise NotImplementedError

    def get_next_task(self):
        raise NotImplementedError

    def requeue(self, task):
        raise NotImplementedError