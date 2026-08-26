class LongTermMemoryModule:
    """Placeholder for durable long-term memory storage."""

    def __init__(self, memory_dir=None):
        self.memory_dir = memory_dir
        self.ready = False

    def store(self, key, value):
        return {"status": "not_implemented", "message": "Long-term memory is not implemented yet."}

    def recall(self, key):
        return {"status": "not_implemented", "message": "No long-term memory entry found yet."}
