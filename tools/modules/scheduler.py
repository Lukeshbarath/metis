class SchedulerModule:
    """Placeholder for task scheduling and reminders."""

    def __init__(self, schedule_dir=None):
        self.schedule_dir = schedule_dir
        self.ready = False

    def add_task(self, task_name, when, payload=None):
        return {"status": "not_implemented", "message": "Scheduling is not implemented yet."}

    def list_tasks(self):
        return {"status": "not_implemented", "message": "No scheduled tasks yet."}
