import psutil
import os
import time


class ResourceManager:
    def __init__(self):
        # Real system limits (read-only view)
        self.total_memory = psutil.virtual_memory().total / (1024 ** 3)  # in GB

        # Dynamic values
        self.available_memory = self._get_available_memory()
        self.cpu_usage = 0.0

        # Battery (real if available, else simulated fallback)
        self.has_battery = psutil.sensors_battery() is not None
        self.total_battery = 100.0
        self.current_battery = self._get_battery_level()

        # Internal tracking
        self.active_tasks = set()

    def _get_available_memory(self):
        mem = psutil.virtual_memory()
        return mem.available / (1024 ** 3)  # GB

    def _get_cpu_usage(self):
        return psutil.cpu_percent(interval=0.1)

    def _get_battery_level(self):
        if self.has_battery:
            battery = psutil.sensors_battery()
            return battery.percent if battery else 100.0
        else:
            # fallback simulated battery
            return getattr(self, "current_battery", 100.0)

    def refresh(self):
        """Refresh real system stats"""
        self.available_memory = self._get_available_memory()
        self.cpu_usage = self._get_cpu_usage()
        self.current_battery = self._get_battery_level()

    def allocate(self, task):
        """
        Decide if a task can run based on REAL system constraints
        """
        self.refresh()

        # Policy constraints (you can tune these)
        if self.available_memory < 0.2:  # <200MB approx
            return False

        if self.cpu_usage > 90:  # CPU overloaded
            return False

        if self.current_battery <= 5:
            return False

        # Track active task
        self.active_tasks.add(task.tid)
        return True

    def release(self, task):
        """Release task tracking (OS handles actual memory)"""
        if task.tid in self.active_tasks:
            self.active_tasks.remove(task.tid)

    def consume_energy(self, task):
        """
        Simulate energy drain ONLY if no real battery
        """
        if not self.has_battery:
            drain = getattr(task, "energy_usage", 0.5)
            self.current_battery -= drain
            if self.current_battery < 0:
                self.current_battery = 0

    def apply_scheduling_policy(self, task):
        """
        Apply OS-level control (THIS is where it becomes 'real')
        """
        try:
            pid = getattr(task, "pid", None)
            if pid:
                p = psutil.Process(pid)

                # Adjust priority (nice value)
                if task.base_priority >= 8:
                    p.nice(-5)  # higher priority
                elif task.base_priority <= 3:
                    p.nice(10)  # lower priority

        except Exception:
            pass  # process may have exited

    def kill_task(self, task):
        """Force terminate a process (real OS control)"""
        try:
            pid = getattr(task, "pid", None)
            if pid:
                p = psutil.Process(pid)
                p.terminate()
        except Exception:
            pass