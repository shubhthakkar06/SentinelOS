from base.scheduler_base import SchedulerBase

class HybridScheduler(SchedulerBase):
    def __init__(self):
        self.tasks = []
        self.execution_count = {}   # track how many times each task ran

    def add_task(self, task):
        task.waiting_time = 0
        self.execution_count[task.tid] = 0
        self.tasks.append(task)

    def compute_score(self, task):
        deadline = task.deadline if task.deadline else 100

    # normalize values
        critical_score = 50 if task.critical else 0
        priority_score = task.base_priority * 5
        aging_score = task.waiting_time * 10
        deadline_score = max(0, 50 - deadline)   # earlier deadline = higher score
        execution_penalty = self.execution_count[task.tid] * 15

    # FINAL SCORE
        score = (
            critical_score +
            priority_score +
            aging_score +
            deadline_score -
            execution_penalty
        )

        return -score   # higher score = higher priority

    def get_next_task(self):
        if not self.tasks:
            return None

        self.tasks.sort(key=self.compute_score)

        task = self.tasks.pop(0)

        # update execution history
        self.execution_count[task.tid] += 1

        # reset waiting time for selected task
        task.waiting_time = 0

        # increase waiting time for others
        for t in self.tasks:
            t.waiting_time += 1

        return task

    def requeue(self, task):
        if task.state != "FAULT":
            self.tasks.append(task)