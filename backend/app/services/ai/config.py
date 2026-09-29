import os

class AIConfig:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "mock").lower()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

config = AIConfig()
