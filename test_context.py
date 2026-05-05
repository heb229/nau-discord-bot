from services.ai.selector import get_embedding_engine
from commands.chatbot import (
    store_thread_message,
    ensure_class_exists,
    ensure_thread_exists,
    ensure_user_exists
)
import asyncio

embedder = get_embedding_engine()

async def run():
    thread_id = "test_thread"
    class_id = "test_class"
    user_id = "user123"

    # Create dependencies FIRST
    ensure_class_exists(class_id)
    ensure_user_exists(user_id)
    ensure_user_exists("bot")
    ensure_thread_exists(thread_id, class_id, "Test Thread")


    await store_thread_message(
        thread_id=thread_id,
        class_id=class_id,
        user_id=user_id,
        content="Hello world",
        embedder=embedder
    )

    print("✅ Insert succeeded!")

asyncio.run(run())


from services.rag.retriever import retrieve_thread_memory

msgs = retrieve_thread_memory(
    thread_id="test_thread",
    question="hello",
    k=5
)

print("Retrieved messages:")
for m in msgs:
    print("-", m)
