from algorithms.priority import PriorityScheduler
from algorithms.edf import EDFScheduler
from algorithms.hybrid import HybridScheduler
from algorithms.round_robin import RoundRobin

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