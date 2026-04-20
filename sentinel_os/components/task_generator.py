import random
import psutil
from sentinel_os.core.task import Task


class TaskGenerator:
    def __init__(self, use_real_processes=True, inject_synthetic=True):
        self.task_id = 0
        self.use_real = use_real_processes
        self.inject_synthetic = inject_synthetic

    def generate_task(self, current_time):
        tasks = []

        # 🔹 1. REAL SYSTEM PROCESSES (Primary Source)
        if self.use_real:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    cpu = proc.info['cpu_percent'] or 0.1
                    mem = proc.info['memory_percent'] or 0.1

                    # Filter trivial processes
                    if cpu < 0.5 and mem < 0.5:
                        continue

                    task = Task(
                        tid=self.task_id,
                        task_type=proc.info['name'],
                        base_priority=self._map_priority(cpu),
                        deadline=current_time + random.randint(10, 30),
                        critical=self._is_critical_process(proc.info['name'])
                    )

                    # 🔥 Attach real OS identity
                    task.pid = proc.info['pid']
                    task.cpu_usage = cpu
                    task.memory_usage = mem
                    task.energy_usage = self._estimate_energy(cpu)

                    tasks.append(task)
                    self.task_id += 1

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        # 🔹 2. SYNTHETIC AUV TASKS (Optional, for demo realism)
        if self.inject_synthetic and random.random() < 0.3:
            for _ in range(random.randint(1, 2)):
                task = Task(
                    tid=self.task_id,
                    task_type=random.choice([
                        "Navigation", "ObstacleAvoidance",
                        "SonarPing", "DepthControl",
                        "BatteryMonitor", "DataLogging"
                    ]),
                    base_priority=random.randint(5, 10),
                    deadline=current_time + random.randint(15, 40),
                    critical=random.choice([True, True, False])  # bias critical
                )

                # Simulated workload
                task.energy_usage = random.uniform(0.5, 2.0)

                tasks.append(task)
                self.task_id += 1

        return tasks

    # -----------------------------
    # 🔧 Helper Functions
    # -----------------------------

    def _map_priority(self, cpu_usage):
        """Map CPU usage → priority (1–10)"""
        if cpu_usage > 50:
            return 10
        elif cpu_usage > 20:
            return 7
        elif cpu_usage > 5:
            return 5
        else:
            return 3

    def _is_critical_process(self, name):
        """Mark important system processes as critical"""
        critical_keywords = [
            "system", "init", "python", "kernel",
            "docker", "ssh", "postgres", "nginx"
        ]
        name = (name or "").lower()
        return any(k in name for k in critical_keywords)

    def _estimate_energy(self, cpu_usage):
        """Rough energy model based on CPU"""
        return max(0.2, cpu_usage / 50.0)