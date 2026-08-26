class VoiceModule:
    """Placeholder for voice input/output integration."""

    def __init__(self, device=None):
        self.device = device
        self.ready = False

    def transcribe(self, audio_path):
        return {"status": "not_implemented", "message": "Voice transcription is not implemented yet."}

    def speak(self, text):
        return {"status": "not_implemented", "message": "Voice synthesis is not implemented yet."}
