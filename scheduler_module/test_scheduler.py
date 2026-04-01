from scheduler_factory import get_scheduler
from base.task import Task

tasks = [
    Task(1, "Navigation", 10, deadline=5, critical=True),
    Task(2, "Obstacle Avoidance", 9, deadline=3, critical=True),
    Task(3, "Sensor", 6, deadline=8),
    Task(4, "Communication", 5),
    Task(5, "Logging", 2)
]

scheduler = get_scheduler("hybrid")

for t in tasks:
    scheduler.add_task(t)

for _ in range(10):
    task = scheduler.get_next_task()
    if not task:
        break

    print(f"Running Task {task.tid} ({task.task_type})")

    task.execute(2)

    if task.state != "FAULT":
        scheduler.requeue(task)
    else:
        print(f"⚠️ Task {task.tid} FAILED")