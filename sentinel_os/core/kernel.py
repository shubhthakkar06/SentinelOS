from sentinel_os.scheduler.scheduler_factory import get_scheduler
from sentinel_os.scheduler.scheduler_base import SchedulerBase
from sentinel_os.core.task import TaskState

class Kernel:
    def __init__(self, policy="hybrid", ai_advisor=None, resource_manager=None):
        self.policy = policy
        self.scheduler = get_scheduler(policy)
        self.resource_manager = resource_manager  # for admission control
        
        if ai_advisor:
            self.scheduler.set_ai_advisor(ai_advisor)

    def add_tasks(self, tasks):
        """
        Add new tasks to the system with Admission Control.
        Critical services are always admitted; transient jobs may be rejected.
        """
        admitted = []
        rejected = []
        
        for task in tasks:
            # 1. Check Admission Control (Backpressure)
            if self.resource_manager:
                current_job_count = len([t for t in self.scheduler.get_queued_tasks() if not t.is_service])
                allowed, reason = self.resource_manager.can_admit_task(task, current_job_count)
                
                if not allowed:
                    rejected.append((task, reason))
                    continue
            
            # 2. Add to scheduler (which places it in the correct state queue)
            self.scheduler.add_task(task)
            admitted.append(task)
            
        return admitted, rejected

    def get_next_task(self, system_state=None):
        """Pick the next task from the scheduler's READY queue."""
        return self.scheduler.get_next_task(system_state)

    def requeue_task(self, task):
        """Move a task back into its appropriate scheduler collection."""
        self.scheduler.requeue(task)
        
    def get_all_tasks(self):
        """Return all tasks across all queues."""
        return self.scheduler.get_queued_tasks()