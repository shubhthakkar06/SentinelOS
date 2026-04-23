class SchedulerBase:
    def __init__(self):
        self.ai_advisor = None
        # Specialized task collections
        self.ready_queue: list = []      # Schedulable tasks (READY)
        self.wait_queue: list = []       # tasks in WAITING (I/O)
        self.blocked_queue: list = []    # tasks in BLOCKED (Resource/Lock)
        self.suspended_queue: list = []  # tasks in SUSPENDED (Halted)

    def set_ai_advisor(self, advisor):
        self.ai_advisor = advisor

    def add_task(self, task):
        """Add a NEW/READY task to the system."""
        raise NotImplementedError

    def get_next_task(self, system_state=None):
        """Pick the next READY task to run from the ready_queue."""
        raise NotImplementedError

    def get_queued_tasks(self):
        """Return a flat list of ALL tasks across all queues (for monitoring)."""
        return self.ready_queue + self.wait_queue + self.blocked_queue + self.suspended_queue

    def requeue(self, task):
        """Move a task to the appropriate collection based on its current state."""
        raise NotImplementedError

    def remove_task(self, task):
        """Remove a task from any collection it might be in."""
        for collection in [self.ready_queue, self.wait_queue, self.blocked_queue, self.suspended_queue]:
            if task in collection:
                collection.remove(task)
                return True
        return False