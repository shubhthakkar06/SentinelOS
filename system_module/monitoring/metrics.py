class Metrics:
    def __init__(self):
        self.faults = []
        self.records = []

    def record_fault(self, fault):
        self.faults.append(fault)

    def record_step(self, data):
        self.records.append(data)

    def summary(self):
        print("\n--- METRICS SUMMARY ---")
        print(f"Total Faults: {len(self.faults)}")
        print(f"Total Steps: {len(self.records)}")