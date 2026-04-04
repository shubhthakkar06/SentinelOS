import random
from system_module.components.resource_manager import ResourceManager
from system_module.components.event_manager import EventManager
from system_module.core.kernel import Kernel
from system_module.components.task_generator import TaskGenerator
from system_module.components.fault_injector import FaultInjector
from system_module.monitoring.metrics import Metrics
from system_module.monitoring.logger import Logger
from system_module.core.context_switch import ContextSwitch

class SystemSimulator:
    def __init__(self):
        self.time = 0
        self.max_time = 50
        self.kernel = Kernel(policy="hybrid")
        self.task_generator = TaskGenerator()
        self.faults_injector = FaultInjector()
        self.event_manager = EventManager()
        self.logger = Logger()
        self.resource_manager = ResourceManager()
        self.metrics = Metrics()
        self.prev_task = None

    def initialize(self):
        self.logger.log("Initializing System")

    def run(self):
        self.logger.log("Starting System")
        while self.time < self.max_time:
            self.event_manager.generate_events(self.time)
            events = self.event_manager.get_events()
            for e in events:
                self.logger.log(f"Event: {e['type']} at time: {e['time']}")

            new_tasks = self.task_generator.generate_task(self.time)
            self.kernel.add_tasks(new_tasks)

            if new_tasks:
                self.logger.log(f"Generated {len(new_tasks)} new tasks")
            task = self.kernel.get_next_task()
            ContextSwitch().switch(self.prev_task, task)

            if task:
                if not hasattr(task, "remaining_time"):
                    task.remaining_time = random.randint(3,8)
                self.logger.log(f"Running task: {task.tid}")
                if not self.resource_manager.allocate(task):
                    self.logger.log("Resource unavailable -> WAITING")
                    task.state = "WAITING"
                    if random.random() < 0.7:
                        self.kernel.requeue_task(task)
                    if task.state == "WAITING":
                        task.state = "READY"
                else:
                    task.execute(2)
                    task.remaining_time -= 2
                    faults = self.faults_injector.inject_task_fault(task, self.time)
                    for f in faults:
                        self.metrics.record_fault(f)
                        self.logger.log(f"Fault {f}")
                        if f["fault_type"] == "RESOURCE_FAILURE":
                            task.state = "WAITING"

                    if task.deadline and self.time > task.deadline and task.remaining_time > 0:
                        self.logger.log(f"Deadline Missed: Task {task.tid} at time: {self.time}")

                    self.resource_manager.release(task)
                    if task.state == "FAULT":
                        if random.random() < 0.5:
                            self.logger.log(f"Task {task.tid} RECOVERED from fault")
                            task.state = "READY"
                            self.kernel.requeue_task(task)
                        else:
                            self.logger.log(f"Task {task.tid} FAILED")
                    elif task.remaining_time <= 0:
                        self.logger.log(f"Task {task.tid} COMPLETED")
                    else:
                        self.kernel.requeue_task(task)

            else:
                self.logger.log(f"IDLE CPU")

            self.metrics.record_step({
                "time": self.time,
                "events": len(events),
                "memory":self.resource_manager.available_memory
            })
            self.prev_task = task
            self.time += 1
        self.logger.log("Finished System")
        self.metrics.summary()
