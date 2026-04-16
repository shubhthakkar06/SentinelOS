class ResourceManager:
    def __init__(self):
        self.total_memory = 100
        self.available_memory = 100
        self.cpu_busy = False
        self.total_battery = 100.0
        self.current_battery = 100.0

    def allocate(self, task):
        # Prevent allocation if battery is dead or memory is too low
        if self.available_memory < 5 or self.current_battery <= 0:
            return False
            
        self.available_memory -= 5
        self.cpu_busy = True
        return True

    def release(self, task):
        self.available_memory += 5
        self.cpu_busy = False
        
    def consume_energy(self, task):
        if self.current_battery > 0:
            # Drain battery based on task's energy usage
            drain = getattr(task, "energy_usage", 1.0)
            self.current_battery -= drain
            if self.current_battery < 0:
                self.current_battery = 0