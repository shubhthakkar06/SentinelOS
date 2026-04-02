import random

class FaultInjector:
    def inject_task_fault(self,task,current_time):
        if random.random() < 0.1:
            return {
                "time": current_time,
                "task_id": task.tid,
                "fault_type":"RESOURCE_FAILURE"
            }
        return None