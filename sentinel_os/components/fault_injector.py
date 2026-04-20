import random
import logging

class FaultInjector:
    """
    Advanced Fault Injector for SentinelOS.
    Features:
      - Scenario-aware probabilities (Connected vs Survival)
      - Fault deduplication (reports unique events only once)
      - Realistic AUV fault types
    """

    def inject_task_fault(self, task, current_time, system_state=None):
        faults = []
        mode = system_state.get("mission_mode", "Connected") if system_state else "Connected"
        
        # 1. Base probabilities based on mission mode
        # Connected: stable (2% chance) | Survival: chaotic (15% chance)
        base_prob = 0.02 if mode == "Connected" else 0.15
        
        # 2. Check for Deadline Miss (Single Record)
        if task.deadline and current_time > task.deadline:
            if "DEADLINE_MISS" not in task.fault_history:
                task.fault_history.add("DEADLINE_MISS")
                faults.append({
                    "time": current_time,
                    "task_id": task.tid,
                    "fault_type": "DEADLINE_MISS"
                })

        # 3. Inject Transient/Subsystem Faults
        if random.random() < base_prob:
            ftype = random.choice([
                "RESOURCE_FAILURE", 
                "SENSOR_DRIFT", 
                "COMM_LAG", 
                "IO_TIMEOUT",
                "BIT_FLIP"
            ])
            
            # For serious faults like RESOURCE_FAILURE, we might want to deduplicate 
            # or allow multiple if they are transient. We'll allow them but limit 
            # to one 'unique' type per task history for cleaner metrics.
            if ftype not in task.fault_history:
                task.fault_history.add(ftype)
                faults.append({
                    "time": current_time,
                    "task_id": task.tid,
                    "fault_type": ftype
                })
        
        return faults