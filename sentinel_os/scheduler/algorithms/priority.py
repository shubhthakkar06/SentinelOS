from sentinel_os.scheduler.scheduler_base import SchedulerBase


class PriorityScheduler(SchedulerBase):
    """
    Static Priority scheduler with aging (prevents starvation).

    Uses `effective_priority` so Priority Inheritance Protocol boosts
    are respected — a lock holder's inherited priority is visible here.
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

        # Sort: critical tasks first, then by effective_priority (descending),
        # then by energy usage ascending (prefer low-energy tasks as tie-break)
        self.tasks.sort(
            key=lambda t: (
                not t.critical,
                -t.effective_priority,
                t.energy_usage,
            )
        )

        task = self.tasks.pop(0)
        task.waiting_time = 0
        for t in self.tasks:
            t.waiting_time += 1
        return task

    def get_queued_tasks(self):
        return list(self.tasks)

    def requeue(self, task):
        from sentinel_os.core.task import TaskState
        if task.state not in (str(TaskState.TERMINATED), "TERMINATED"):
            self.tasks.append(task)