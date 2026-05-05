from dataclasses import dataclass
from typing import List

from services.ai.selector import get_embedding_engine
from services.db import pool


EMBED_DIM = 3072


@dataclass
class RagContext:
    class_chunks: List[str]

# CLASS CONTEXT

# function to retrieve relevant class_doc chunks based on a question and optional tag filters.
def retrieve_class_context(*, class_id: str, selected_tags: List[str], question: str, k: int = 5) -> RagContext:
    """
    Retrieve top-k class_doc chunks for a given class_id and (optional) tag filter.
    Uses halfvec cast so your HNSW halfvec index can be used.
    """
    embedder = get_embedding_engine()
    qvec = embedder.embed([question])[0]

    # if selected_tags is not empty, include a filter in the SQL query to only consider chunks whose tags 
    # overlap with the selected_tags.
    with pool.connection() as conn:
        if selected_tags:
            rows = conn.execute(
                f"""
                SELECT COALESCE(title,'Untitled') AS title, content
                FROM class_docs
                WHERE class_id = %s
                  AND embedding IS NOT NULL
                  AND (tags && %s)
                ORDER BY (embedding::halfvec({EMBED_DIM})) <=> (%s::halfvec({EMBED_DIM}))
                LIMIT %s
                """,
                (class_id, selected_tags, qvec, k),
            ).fetchall()
        # if no tags are selected, skip the tag filter in the SQL query and retrieve top-k chunks based solely on embedding similarity.
        else:
            rows = conn.execute(
                f"""
                SELECT COALESCE(title,'Untitled') AS title, content
                FROM class_docs
                WHERE class_id = %s
                  AND embedding IS NOT NULL
                ORDER BY (embedding::halfvec({EMBED_DIM})) <=> (%s::halfvec({EMBED_DIM}))
                LIMIT %s
                """,
                (class_id, qvec, k),
            ).fetchall()

    # combine title and content for each retrieved chunk into a single string, and return as RagContext.
    chunks = [f"{title}:\n{content}" for (title, content) in rows]
    return RagContext(class_chunks=chunks)

# function to convert retrieved chunks into the same kind of string your existing ChatResponder expects.
def pack_context(ctx: RagContext) -> str:
    """
    Convert retrieved chunks into the same kind of string your existing ChatResponder expects.
    """
    if not ctx.class_chunks:
        return ""
    return "=== CLASS CONTEXT (retrieved) ===\n" + "\n\n".join(ctx.class_chunks)


# THREAD CONTEXT

# function to retrieve relevant thread_memory chunks based on a question, with an option to retrieve recent messages if the 
# question is empty or only whitespace.
def retrieve_thread_memory(thread_id: str, question: str, k: int = 5) -> list[str]:
    if k <= 0:
        return []

    if not question.strip():
        return retrieve_recent_thread_memory(thread_id=thread_id, k=k)

    embedder = get_embedding_engine()
    qvec = embedder.embed([question])[0]

    # retrieve top-k relevant chunks from thread_memory based on embedding similarity to the question. 
    #    Note: k is number (like n number of items; this is just k number of chucks where k can be any number)
    # If the question is empty or only whitespace, retrieve the most recent messages instead.
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT content
            FROM thread_memory
            WHERE thread_id = %s
              AND embedding IS NOT NULL
            ORDER BY (embedding::halfvec({EMBED_DIM})) <=> (%s::halfvec({EMBED_DIM}))
            LIMIT %s
            """,
            (thread_id, qvec, k)
        ).fetchall()

    print(f"\n----------\nRetrieved {len(rows)} semantic matches for thread {thread_id}\n----------\n")
    # combine the retrieved chunks into a list of strings and return.
    return [r[0] for r in rows]

# function to retrieve the most recent messages from thread_memory for a given thread_id, limited by k.
def retrieve_recent_thread_memory(thread_id: str, k: int = 5) -> list[str]:
    if k <= 0:
        return []

    # retrieve the most recent messages from thread_memory for the given thread_id, 
    # ordered by creation time in descending order, and limited to k.
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT content
            FROM thread_memory
            WHERE thread_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (thread_id, k)
        ).fetchall()

    # reverse the order
    rows.reverse()
    print(f"\n----------\nRetrieved {len(rows)} recent messages for thread {thread_id}\n----------\n")
    
    # combine the retrieved messages into a list of strings and return.
    return [r[0] for r in rows]
