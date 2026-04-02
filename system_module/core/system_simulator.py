import random
from logging import Logger

from system_module.core.kernel import Kernel
from system_module.components.task_generator import TaskGenerator
from system_module.components.fault_injector import FaultInjector
from system_module.monitoring.metrics import Metrics
from system_module.monitoring.logger import Logger

class SystemSimulator:
    def __init__(self):
        self.time = 0
        self.max_time = 50
        self.completed_tasks = []
        self.failed_tasks = []

        self.kernel = Kernel(policy="hybrid")
        self.task_generator = TaskGenerator()
        self.fault_injector = FaultInjector()
        self.metrics = Metrics()
        self.logger = Logger()

    def initialize(self):
        self.logger.log("Initializing System..")
        self.time = 0

    def run(self):
        self.logger.log("Simulation Started")
        while self.time < self.max_time:
            self.logger.log(f"\nTIME: {self.time}")

            new_tasks = self.task_generator.generate_task(self.time)
            if new_tasks:
                self.logger.log(f"Generated {len(new_tasks)} task(s)")
            self.kernel.add_tasks(new_tasks)
            task = self.kernel.get_next_task()

            if task:
                self.logger.log(f"->Running task {task.tid} ({task.task_type})")
                exec_time = task.execute(time_slice=2)
                fault = self.fault_injector.inject_task_fault(task, self.time)

                if fault:
                    self.metrics.record_fault(fault)
                    self.logger.log(f"⚠ Fault Injected: {fault}")

                if task.state == "FAULT":
                    self.logger.log(f"Task {task.tid} FAILED")
                    self.failed_tasks.append(task)
                else:
                    self.kernel.requeue_task(task)
                    if task.state == "WAITING":
                        self.logger.log(f"Task {task.tid} WAITING")
                    else:
                        self.logger.log(f"Task {task.tid} continues")
                    self.completed_tasks.append(task)
            else:
                self.logger.log("Idle CPU")
            self.metrics.update(
                time = self.time,
                active_tasks = len(self.completed_tasks),
                failed_tasks = len(self.failed_tasks)
            )
            self.time += 1
        self.logger.log("\nSimulation Finished")
        self.metrics.summary()