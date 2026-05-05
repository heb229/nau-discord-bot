from pathlib import Path

from commands.constants import *
from services.ai.model_engine import ResponseEngine
from services.ai.selector import get_response_engine

# This ChatResponder class is responsible for generating responses to student questions in a 
# university computer science course context.
SYSTEM_PROMPT = """
You are a university teaching assistant for a computer science course.

STRICT RULES:
- Do NOT provide solutions to homework, quizzes, or exam questions.
- Do NOT write full code or algorithms.
- Do NOT give final numeric or symbolic answers.
- You MAY explain concepts at a high level.
- You MAY clarify definitions and intuition.
- You MUST align explanations with the provided course material.
- If a question appears to ask for an answer, refuse and explain the concept instead.

Tone:
Helpful, encouraging, academic.
"""

# The ChatResponder class takes in a guild ID, optional context (either as a file path or raw text), 
# and an optional AI engine. It generates responses to student questions while enforcing academic 
# integrity by ensuring that the responses do not include code, final answers, or step-by-step 
# solutions. The class uses a system prompt to guide the tone and content of the responses, and 
# it can adjust the length and verbosity of the explanations based on parameters.
class ChatResponder:
    def __init__(
        self,
        guild_id: int,
        context_path: Path | None = None,
        raw_context: str | None = None,
        engine: ResponseEngine | None = None,
    ):
        if raw_context:
            self.context = raw_context[:CONTEXT_LIMIT]
        elif context_path:
            self.context = context_path.read_text(encoding="utf-8")[:CONTEXT_LIMIT]
        else:
            self.context = ""

        self.engine = engine or get_response_engine()

    def generate(
        self,
        question: str,
        allow_long: bool = False,
        enforce_integrity: bool = True,
        verbosity: str = "detailed",
    ) -> str:
        if allow_long:
            length_instruction = "Provide a detailed explanation. Length is not restricted."
        else:
            length_instruction = (
                f"Your response MUST be under {MAX_DISCORD_LEN} characters. "
                "If the explanation exceeds this, shorten it."
            )

        verbosity_instruction = {
            "concise": "Keep the response brief and direct, focusing only on the key explanation.",
            "normal": "Keep the response moderately detailed and easy to follow.",
            "detailed": "Provide a detailed explanation with strong conceptual clarity.",
        }.get(verbosity, "Provide a detailed explanation with strong conceptual clarity.")

        prompt = f"""
            {length_instruction}
            {verbosity_instruction}
            {SYSTEM_PROMPT}

            COURSE and CONVERSATION CONTEXT (multiple topics, consider ALL sections below):
            {self.context}

            STUDENT QUESTION:
            {question}

            Instructions:
            - Make sure to use information from all the provided contexts.
            - If multiple topics are referenced, cover them all as needed.
            - Explain concepts clearly, but do NOT give full solutions or code.
            - Use THREAD CONTEXT to maintain continuity in the conversation
            - Do not repeat explanations unnecessarily
            - Build on previous answers if relevant
            """

        print("Calling AI engine...")
        print("Prompt length:", len(prompt))
        print(prompt)
        try:
            text = self.engine.generate(prompt)
        except Exception as err:
            print(f"{self.engine.__class__.__name__} failed:", err)
            raise

        print("AI engine responded.")

        if "```" in text:
            print("Caught code block in response!")
            return (
                "I can explain the concept, but I can't provide code or full solutions.\n\n"
                "Try asking *why* or *how* the concept works."
            )

        if enforce_integrity:
            integrity_prompt = f"""
            Instructions:
            - Ensure this explanation DOES NOT include:
                * Full code
                * Step-by-step solutions
                * Final numeric or symbolic answers
            - Only explain concepts, intuition, or general guidance
            - Keep the explanation helpful, academic, and clear

            THIS IS FOR STUDENTS. It will be sent to someone learning computer science.

            Return the cleaned explanation, for academic integrity.

            The following AI response needs to be checked. Only reply with the cleaned version
            if it is not already clean. If it is clean, then do not change the text.:

            {text}
            """
            print("Calling AI engine for academic integrity pass...")

            try:
                text = self.engine.generate(integrity_prompt)
            except Exception as err:
                print("Integrity pass failed:", err)
                raise
            print("Academic integrity pass complete.")

        return text
