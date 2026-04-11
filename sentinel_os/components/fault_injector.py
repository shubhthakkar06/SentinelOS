import random

class FaultInjector:
    def inject_task_fault(self,task,current_time):
        faults = []
        if random.random() < 0.1:
             faults.append({
                "time": current_time,
                "task_id": task.tid,
                "fault_type":"RESOURCE_FAILURE"
            })
        if task.deadline and current_time > task.deadline:
            faults.append({
                "time": current_time,
                "task_id": task.tid,
                "fault_type": "DEADLINE_MISS"
            })
        return faults