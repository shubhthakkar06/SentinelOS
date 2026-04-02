class Metrics:
    def __init__(self):
        self.faults = []
        self.history = []

    def record_fault(self, fault):
        self.faults.append(fault)

    def update(self, **kwargs):
        self.history.append(kwargs)

    def summary(self):
        print("\n--- METRICS SUMMARY ---")
        print(f"Total Faults: {len(self.faults)}")
        print(f"Total Steps: {len(self.history)}")