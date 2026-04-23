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
            "depth",
            "hull_integrity",
            "water_temp",
            "recommended_priority",
            "fault_occurred"
        ]

    def record_sample(self, time, task, memory, env_data, recommended_priority, fault_occurred):
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
                "depth": env_data.get('depth', 0),
                "hull_integrity": env_data.get('hull_integrity', 100),
                "water_temp": env_data.get('water_temperature', 20),
                "recommended_priority": recommended_priority,
                "fault_occurred": 1 if fault_occurred else 0
            })
