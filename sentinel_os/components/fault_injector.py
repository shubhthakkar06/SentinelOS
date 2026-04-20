import random
import psutil
from collections import defaultdict


class FaultInjector:
    def __init__(self):
        # Track past faults per task/system
        self.task_fault_history = defaultdict(list)
        self.system_stress = 0  # accumulates over time

    def inject_task_fault(self, task, current_time, system_state=None):
        faults = []

        cpu = psutil.cpu_percent(interval=0.05)
        mem = psutil.virtual_memory().percent

        # Update system stress (persistent behavior)
        self.system_stress = (cpu * 0.6 + mem * 0.4) / 100

        task_history = self.task_fault_history[task.tid]

        # --------------------------------------------------
        # 1. DEADLINE FAILURE (deterministic escalation)
        # --------------------------------------------------
        if task.deadline and current_time > task.deadline:
            severity = "HIGH" if task.critical else "MEDIUM"

            faults.append(self._create_fault(
                task, current_time,
                "DEADLINE_MISS",
                severity
            ))

        # --------------------------------------------------
        # 2. SYSTEM STRESS FAULT (emergent behavior)
        # --------------------------------------------------
        if self.system_stress > 0.85:
            chance = 0.4 + (len(task_history) * 0.1)

            if random.random() < min(chance, 0.8):
                faults.append(self._create_fault(
                    task,
                    current_time,
                    "SYSTEM_OVERLOAD",
                    "HIGH"
                ))

        # --------------------------------------------------
        # 3. MEMORY PRESSURE CASCADE
        # --------------------------------------------------
        if mem > 85:
            chance = 0.2 + (mem - 85) / 50

            if random.random() < chance:
                faults.append(self._create_fault(
                    task,
                    current_time,
                    "MEMORY_PRESSURE",
                    "HIGH" if mem > 92 else "MEDIUM"
                ))

        # --------------------------------------------------
        # 4. CPU STARVATION (scheduler-level realism)
        # --------------------------------------------------
        if cpu > 80:
            starvation_risk = cpu / 100 * (1 + len(task_history) * 0.05)

            if random.random() < starvation_risk:
                faults.append(self._create_fault(
                    task,
                    current_time,
                    "CPU_STARVATION",
                    "MEDIUM"
                ))

        # --------------------------------------------------
        # 5. TASK INSTABILITY (fault history matters)
        # --------------------------------------------------
        if len(task_history) >= 2:
            if random.random() < 0.3:
                faults.append(self._create_fault(
                    task,
                    current_time,
                    "RECURRING_FAILURE",
                    "MEDIUM"
                ))

        # --------------------------------------------------
        # 6. TRANSIENT GLITCH (rare noise)
        # --------------------------------------------------
        if random.random() < 0.03:
            faults.append(self._create_fault(
                task,
                current_time,
                "TRANSIENT_GLITCH",
                "LOW"
            ))

        # --------------------------------------------------
        # 7. TASK FAILURE (final collapse condition)
        # --------------------------------------------------
        if hasattr(task, "remaining_time") and task.remaining_time <= 0:
            collapse_chance = 0.2 + len(task_history) * 0.15

            if random.random() < min(collapse_chance, 0.9):
                faults.append(self._create_fault(
                    task,
                    current_time,
                    "TASK_COLLAPSE",
                    "HIGH"
                ))

        # Store history (important for realism)
        if faults:
            self.task_fault_history[task.tid].extend(faults)

        return faults

    # --------------------------------------------------
    # Helper
    # --------------------------------------------------
    def _create_fault(self, task, time, fault_type, severity):
        return {
            "time": time,
            "task_id": task.tid,
            "fault_type": fault_type,
            "severity": severity,
            "critical_task": getattr(task, "critical", False),
            "system_stress": round(self.system_stress, 2)
        }