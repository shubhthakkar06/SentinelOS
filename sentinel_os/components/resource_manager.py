class ResourceManager:
    def __init__(self):
        self.total_memory = 100
        self.available_memory = 100
        self.cpu_busy = False

    def allocate(self, task):
        if self.available_memory < 5:
            return False
        self.available_memory -= 5
        self.cpu_busy = True
        return True

    def release(self, task):
        self.available_memory += 5
        self.cpu_busy = False