import random

class EventManager:
    def __init__(self):
        self.events = []

    def generate_events(self, current_time):
        if random.random() < 0.2:
            event = {
                "time": current_time,
                "type":random.choice(["IO_INTERRUPT", "TIMER_INTERRUPT"])
            }
            self.events.append(event)

    def get_events(self):
        events = self.events[:]
        self.events.clear()
        return events