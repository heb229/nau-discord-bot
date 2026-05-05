import os

from dotenv import load_dotenv

from services.ai.selector import get_response_engine
from services.chatbot.responder import ChatResponder


load_dotenv()


def test_engine_generate() -> None:
    engine = get_response_engine()
    prompt = "In 2-3 sentences, explain what recursion is in computer science."

    print(f"Using response engine: {engine.__class__.__name__}")
    print("\nCalling engine.generate()...\n")
    text = engine.generate(prompt)
    print("Response:")
    print(text)


def test_chat_responder_generate() -> None:
    context = """
    COURSE CONTEXT:
    Recursion is a technique where a function solves a problem by calling itself on a smaller version of the same problem.
    A base case stops the recursive process.

    THREAD CONTEXT:
    The student is confused about how recursion eventually stops.
    """

    responder = ChatResponder(
        guild_id=0,
        raw_context=context,
        engine=get_response_engine(),
    )

    question = "Can you explain recursion and why base cases matter?"

    print("\nCalling ChatResponder.generate()...\n")
    text = responder.generate(
        question,
        allow_long=True,
        enforce_integrity=True,
        verbosity="normal",
    )
    print("Response:")
    print(text)


def main() -> None:
    mode = os.getenv("TEST_GENERATE_MODE", "responder").strip().lower()

    if mode == "engine":
        test_engine_generate()
        return

    if mode == "responder":
        test_chat_responder_generate()
        return

    raise RuntimeError("TEST_GENERATE_MODE must be 'engine' or 'responder'")


if __name__ == "__main__":
    main()
