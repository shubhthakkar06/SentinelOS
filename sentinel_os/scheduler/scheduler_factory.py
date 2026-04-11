from sentinel_os.scheduler.algorithms.priority import PriorityScheduler
from sentinel_os.scheduler.algorithms.edf import EDFScheduler
from sentinel_os.scheduler.algorithms.hybrid import HybridScheduler
from sentinel_os.scheduler.algorithms.round_robin import RoundRobin

def get_scheduler(name):
    if name == "priority":
        return PriorityScheduler()
    elif name == "edf":
        return EDFScheduler()
    elif name == "hybrid":
        return HybridScheduler()
    elif name == "rr":
        return RoundRobin()
    else:
        raise ValueError("Unknown scheduler")