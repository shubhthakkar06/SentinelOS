class ContextSwitch:
    def switch(self, prev_task, next_task):
        prev_id = prev_task.tid if prev_task else None
        next_id = next_task.tid if next_task else None
        print(f"[CTX] switch from {prev_id} to {next_id}")