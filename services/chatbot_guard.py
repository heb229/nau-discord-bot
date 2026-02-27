# imports
import re
from services.ai_engine import AIEngine
from services.gemini_engine import GeminiEngine

# FOR: CHATBOT
class ChatGuard:
    # restricted words
    RESTRICTED_PATTERNS = [
        r"solve",
        r"answer",
        r"implement",
        r"write a program",
        r"code this",
        r"give me the solution",
    ]

    def __init__(self, engine: AIEngine | None = None):
        # allow injecting AI engine for response cleaning
        self.engine = engine or GeminiEngine()

    # function to classify questions if restricted
    def classify(self, question: str) -> str:
        question = question.lower()
        for pattern in self.RESTRICTED_PATTERNS:
            if re.search(pattern, question):
                return "restricted"
        return "conceptual"

    # function to enforce integrity
        # it is a "second pass" of the response to double check it
    def enforce_academic_integrity(self, response: str) -> str:
        """
        Take an AI-generated response and ensure it does not include
        code, solutions, or final answers. Returns a cleaned version.
        """
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
