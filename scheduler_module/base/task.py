import random

class Task:
    def __init__(self, tid, task_type, base_priority, deadline=None, critical=False):
        self.tid = tid
        self.task_type = task_type
        self.base_priority = base_priority
        self.deadline = deadline
        self.critical = critical

        self.state = "READY"
        self.energy_usage = random.uniform(0.5, 2.0)

    def execute(self, time_slice):
        exec_time = random.uniform(0.5, time_slice)

        # simulate behavior
        if random.random() < 0.02:
            self.state = "FAULT"
        elif random.random() < 0.2:
            self.state = "WAITING"
        else:
            self.state = "READY"

        return exec_time