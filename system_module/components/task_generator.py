import random
from scheduler_module.base.task import Task

class TaskGenerator:
    def __init__(self):
        self.task_id = 0

    def generate_task(self, current_time):
        tasks = []

        if random.random() < 0.4:
            num_tasks = random.randint(1, 2)
            for _in in range(num_tasks):
                task = Task(
                    tid = self.task_id,
                    task_type= random.choice(["CPU","IO"]),
                    base_priority = random.randint(1,10),
                    deadline = current_time+random.randint(15,40),
                    critical = random.choice([True, False])
                )
                tasks.append(task)
                self.task_id += 1

        return tasks