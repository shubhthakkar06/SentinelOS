import csv
import os

class DatasetGenerator:
    def __init__(self, filename="data/auv_task_data.csv"):
        self.filename = filename
        self.file_exists = os.path.isfile(self.filename)
        self.fieldnames = [
            "system_time", 
            "task_id", 
            "task_type", 
            "base_priority", 
            "is_critical", 
            "remaining_time", 
            "available_memory", 
            "fault_occurred"
        ]

    def record_sample(self, time, task, memory, fault_occurred):
        with open(self.filename, mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if not self.file_exists:
                writer.writeheader()
                self.file_exists = True
            
            writer.writerow({
                "system_time": time,
                "task_id": task.tid,
                "task_type": task.task_type,
                "base_priority": task.base_priority,
                "is_critical": 1 if task.critical else 0,
                "remaining_time": getattr(task, "remaining_time", 0),
                "available_memory": memory,
                "fault_occurred": 1 if fault_occurred else 0
            })
