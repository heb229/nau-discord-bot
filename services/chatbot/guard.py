# imports
import re

from services.ai.model_engine import ResponseEngine
from services.ai.selector import get_response_engine

# This ChatGuard class is responsible for enforcing academic integrity in the chatbot's responses. 
# It checks if a question contains restricted patterns that indicate a request for direct solutions, 
# and it can clean AI-generated responses to ensure they do not include code, final answers, or 
# step-by-step solutions. The class uses an AI engine (like Gemini) to perform the cleaning of 
# responses while maintaining helpful and academic explanations.
class ChatGuard:
    RESTRICTED_PATTERNS = [
        r"solve",
        r"answer",
        r"implement",
        r"write a program",
        r"code this",
        r"give me the solution",
    ]

    def __init__(self, engine: ResponseEngine | None = None):
        self.engine = engine or get_response_engine()

    def classify(self, question: str) -> str:
        question = question.lower()
        for pattern in self.RESTRICTED_PATTERNS:
            if re.search(pattern, question):
                return "restricted"
        return "conceptual"

    def enforce_academic_integrity(self, response: str) -> str:
        integrity_prompt = f"""
        You received the following response from another AI attempt:

        {response}

        Instructions:
        - Ensure this explanation DOES NOT include:
            * Full code
            * Final answers (numeric or symbolic)
            * Step-by-step solutions to homework, quizzes, or exams
        - Only explain concepts, intuition, or general guidance
        - Keep the explanation helpful, academic, and clear

        Return the cleaned version of the explanation.
        """

        print("Running academic integrity check...")
        return self.engine.generate(integrity_prompt)
