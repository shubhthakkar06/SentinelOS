from sentinel_os.scheduler.scheduler_base import SchedulerBase


class EDFScheduler(SchedulerBase):
    """
    Earliest Deadline First scheduler.
    Tasks with the closest deadline run first.
    When deadlines are equal, effective_priority breaks ties (supports PIP).
    """

    def __init__(self):
        super().__init__()
        self.tasks = []

    def add_task(self, task):
        task.waiting_time = 0
        self.tasks.append(task)

    def get_next_task(self, system_state=None):
        if not self.tasks:
            return None

        self.tasks.sort(
            key=lambda t: (
                t.deadline if t.deadline else float('inf'),
                -t.effective_priority,   # tie-break: higher priority first
            )
        )

        task = self.tasks.pop(0)
        # increment waiting time for remaining tasks
        for t in self.tasks:
            t.waiting_time += 1
        return task

    def get_queued_tasks(self):
        return list(self.tasks)

    def requeue(self, task):
        from sentinel_os.core.task import TaskState
        if task.state not in (str(TaskState.TERMINATED), "TERMINATED"):
            self.tasks.append(task)