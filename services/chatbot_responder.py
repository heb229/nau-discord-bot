from pathlib import Path
from services.ai_engine import AIEngine
from services.gemini_engine import GeminiEngine
from commands.constants import *

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

# Class for the responder
class ChatResponder:

    # init (set self)
    def __init__(
        self,
        guild_id: int,
        context_path: Path | None = None,
        raw_context: str | None = None,
        engine: AIEngine | None = None):
        """
        Either provide:
        - context_path (single file), OR
        - raw_context (already merged text)
        """

        if raw_context:
            self.context = raw_context[:CONTEXT_LIMIT]
        elif context_path:
            self.context = context_path.read_text(encoding="utf-8")[:CONTEXT_LIMIT]
        else:
            self.context = ""

        # set engine to selected, or default to gemini
        self.engine = engine or GeminiEngine()

    # generate the actual response
        # 1. take in user question and context 
        # 2. send it to LLM
        # 3. LLM generates response
        # 4. LLM sends itself its own response, with the secondary integrity prompt
        # 5. LLM sends this new response to the user
    def generate(
        self,
        question: str,
        allow_long: bool = False,
        enforce_integrity: bool = True) -> str:

        # if the student is fine with long messages, don't restrict response
        if allow_long:
            length_instruction = (
                "Provide a detailed explanation. Length is not restricted."
            )
        # otherwise, restrict response length
        else:
            length_instruction = (
                f"Your response MUST be under {MAX_DISCORD_LEN} characters. "
                "If the explanation exceeds this, shorten it."
            )

        # PROMPT: explicitly instruct the AI to consider all contexts
        prompt = f"""
            {length_instruction}
            {SYSTEM_PROMPT}

            COURSE CONTEXT (multiple topics, consider ALL sections below):
            {self.context}

            STUDENT QUESTION:
            {question}

            Instructions:
            - Make sure to use information from all the provided contexts.
            - If multiple topics are referenced, cover them all as needed.
            - Explain concepts clearly, but do NOT give full solutions or code.
            """

        print("Calling AI engine...")
        print("Prompt length:", len(prompt))
        print(prompt)
        text = self.engine.generate(prompt)
        print("AI engine responded.")

        # safety check for code blocks
        if "```" in text:
            print("Caught code block in response!")
            return (
                "I can explain the concept, but I can't provide code or full solutions.\n\n"
                "Try asking *why* or *how* the concept works."
            )


        # secondary academic integrity check
            # takes first response from LLM and runs it back into LLM
            # to check integrity

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
            text = self.engine.generate(integrity_prompt)
            print("Academic integrity pass complete.")

        return text

