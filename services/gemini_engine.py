import os
from google import genai
from dotenv import load_dotenv

from services.ai_engine import AIEngine

# load env file in
load_dotenv()


# Engine class for gemini
class GeminiEngine(AIEngine):
    """
    Gemini-based AI engine using Google AI Studio API.
    """

    def __init__(self, model: str = "gemini-3-flash-preview"):
        self.client = genai.Client(
            api_key = os.getenv("GEMINI_API_KEY"))
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model = self.model,
            contents = prompt)

        return response.text.strip()
