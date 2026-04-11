from sentinel_os.scheduler.scheduler_base import SchedulerBase

class HybridScheduler(SchedulerBase):
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.execution_count = {}   # track how many times each task ran

    def add_task(self, task):
        task.waiting_time = 0
        self.execution_count[task.tid] = 0
        self.tasks.append(task)

    def compute_score(self, task, system_state=None):
        deadline = task.deadline if task.deadline else 100

    # normalize values
        critical_score = 50 if task.critical else 0
        priority_score = task.base_priority * 5
        aging_score = task.waiting_time * 10
        deadline_score = max(0, 50 - deadline)   # earlier deadline = higher score
        execution_penalty = self.execution_count[task.tid] * 15

        ai_boost = 0
        if self.ai_advisor and system_state is not None:
            raw_boost = self.ai_advisor.get_advisory_signal(task, system_state)
            ai_boost = raw_boost * 10
            # Print a highly visible alert if the AI intervenes!
            if ai_boost > 0:
                print(f"\033[96m[⚡ AI ADVISOR] Predicting potential fault! Boosted Task {task.tid} ({task.task_type}) Priority by +{raw_boost}\033[0m")
            
    # FINAL SCORE
        score = (
            critical_score +
            priority_score +
            aging_score +
            deadline_score +
            ai_boost -
            execution_penalty
        )

        return -score   # higher score = higher priority

    def get_next_task(self, system_state=None):
        if not self.tasks:
            return None

        self.tasks.sort(key=lambda t: self.compute_score(t, system_state))

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