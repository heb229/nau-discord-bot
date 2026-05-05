# this is a test script to test the retrivel process of our vector database.

# Test Steps:
    # Sets Query
    # Sets Tags
    # Sets embeding model through our Engine file
    # Sets query vector (embeds our query)
    # Sets DB connection pool (ordered by embedding match with set limit)
    # Displays top n semantic matches

import os
from services.db import pool
from services.gemini_embed_engine import GeminiEmbedEngine

def main():
    class_id = os.environ.get("TEST_CLASS_ID")
    if not class_id:
        raise RuntimeError("Set TEST_CLASS_ID env var to your guild/class id")

    query = "Explain recursion and base cases"
    tags = ["recursion"]

    emb = GeminiEmbedEngine()
    qvec = emb.embed([query])[0]

    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(title,'Untitled'), content
            FROM class_docs
            WHERE class_id=%s AND embedding IS NOT NULL
            ORDER BY (embedding::halfvec(3072)) <=> (%s::halfvec(3072))
            LIMIT 5
            """,
            (class_id, qvec),
        ).fetchall()

    print("Top hits:")
    for t, c in rows:
        print("\n---", t, "---\n", c[:400])

if __name__ == "__main__":
    main()


