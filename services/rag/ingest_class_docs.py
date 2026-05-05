import hashlib
import json
from pathlib import Path

from services.ai.selector import get_embedding_engine
from services.db import pool


# ---------- Chunking / hashing ----------

# Simple chunking strategy: split into max_chars with some overlap to preserve context. Adjust as needed.
def chunk_text(text: str, max_chars: int = 1800, overlap: int = 200) -> list[str]:
    # strip text and make sure it exists before chunking
    text = text.strip()
    if not text:
        return []
    
    # chunk the text with the specified max characters and overlap
    chunks: list[str] = []
    index = 0
    # for the whole text, create chunks of max_chars length, with the specified overlap, and add them to the chunks list
    while index < len(text):
        end = min(len(text), index + max_chars)
        chunks.append(text[index:end])

        # if we've reached the end of the text, break the loop. 
        # Otherwise, move the index back by the overlap amount to create overlapping chunks.
        if end == len(text):
            break

        # move back by overlap for the next chunk
        index = max(0, end - overlap)
    return chunks

# Simple hashing strategy: SHA-1 of class_id + source_ref + chunk content. This helps with deduplication and re-ingestion.
def sha1(s_string: str) -> str:
    # create a SHA-1 hash of the input string, which is a combination of class_id, source_ref, and chunk content. 
    # This will be used to identify unique chunks and avoid duplicates in the database.
    return hashlib.sha1(s_string.encode("utf-8")).hexdigest()



# ---------- .meta.json support ----------

# function to get the path of the meta file for a given text file. 
# For example, if the text file is "recursion.txt", the meta file would be "recursion.meta.json" in the same directory.
def meta_path_for_text(fp: Path) -> Path:
    # recursion.txt -> recursion.meta.json
    return fp.with_suffix(".meta.json")

# function to load the meta information from the corresponding .meta.json file.
# Note: fp stands for "file path" and mp stands for "meta path".
def load_meta(fp: Path) -> dict:
    mp = meta_path_for_text(fp)
    if not mp.exists():
        return {}
    try:
        return json.loads(mp.read_text(encoding = "utf-8"))
    except Exception as err:
        print(f"WARNING: Failed to parse meta file {mp}: {err}")
        return {}

# function to normalize tags by stripping whitespace, converting to lowercase, and replacing spaces with underscores.
def normalize_tag(text: str) -> str:
    return text.strip().lower().replace(" ", "_")

# function to merge primary tags (inferred from filename) and extra tags (provided in meta), 
# while normalizing and deduplicating them.
def merge_tags(primary: list[str], extra: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []

    # iterate through both primary and extra tags, normalize them, and add to the output list if they haven't been seen before.
    for t in primary + extra:
        nt = normalize_tag(str(t))
        if nt and nt not in seen:
            seen.add(nt)
            out.append(nt)
    return out



# ---------- Inference helpers ----------

# function to infer document type based on filename and meta information.
def infer_doc_type(fp: Path, meta: dict) -> str:
    # meta can override
    if isinstance(meta.get("doc_type"), str) and meta["doc_type"].strip():
        return meta["doc_type"].strip().lower()

    # otherwise infer from path
    if fp.name.lower() == "general.txt":
        return "general"

    parent = fp.parent.name.lower()
    if parent.endswith("s"):
        parent = parent[:-1]  # concepts -> concept, projects -> project
    return parent or "misc"

# function to infer tags based on filename and meta information.
def infer_tags(fp: Path, meta: dict) -> list[str]:
    # primary tag from filename stem
    primary = [fp.stem]

    # extra tags from meta
    extra = meta.get("tags", [])
    if not isinstance(extra, list):
        extra = []

    return merge_tags(primary, extra)

# function to infer title based on filename and meta information.
def infer_title(fp: Path, meta: dict) -> str:
    if isinstance(meta.get("title"), str) and meta["title"].strip():
        return meta["title"].strip()
    return fp.stem



# ---------- Main ingestion ----------
# function to ingest all .txt files in a given folder for a specific class, along with their metadata, into the database.
def ingest_class_folder(class_id: str, folder: Path):
    embedder = get_embedding_engine()

    # ensure class exists in the database (idempotent)
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO classes (class_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (class_id,),
        )

    # find all .txt files in the folder and its subfolders. If no .txt files are found, print a message and return.
    files = list(folder.rglob("*.txt"))
    if not files:
        print(f"No .txt files found under {folder}")
        return

    # for each .txt file, load its meta information, read its content, chunk it, embed the chunks, 
    # infer document type, tags, and title, and then store the chunks in the database with their 
    # embeddings and metadata. If a file has already been ingested (based on source_ref), 
    # it will be re-ingested with the new content and metadata.
    for fp in files:
        meta = load_meta(fp)

        content = fp.read_text(encoding="utf-8")
        chunks = chunk_text(content)
        if not chunks:
            continue

        vectors = embedder.embed(chunks)

        doc_type = infer_doc_type(fp, meta)
        tags = infer_tags(fp, meta)
        title = infer_title(fp, meta)
        source_ref = fp.as_posix()

        # Re-ingest-safe: remove previous chunks for this file (as is, make sure there is no duplicate data if the same file is 
        # ingested again, which may be the case if an instructor updates a file and re-runs the ingestion script. 
        # This ensures that the database only contains the latest version of each document, without duplicates from previous ingestions.)
        with pool.connection() as conn:
            conn.execute(
                "DELETE FROM class_docs WHERE class_id=%s AND source_ref=%s",
                (class_id, source_ref),
            )

        # store new chunks with embeddings and metadata. Each chunk is stored with a hash that combines the 
        # class_id, source_ref, and chunk content, 
        # which helps with deduplication and tracking of unique chunks in the database.
        with pool.connection() as conn:
            for chunk, vec in zip(chunks, vectors):
                hash_type = sha1(f"{class_id}|{source_ref}|{chunk}")
                conn.execute(
                    """
                    INSERT INTO class_docs
                      (class_id, doc_type, tags, title, content, content_hash, source_ref, embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (class_id, doc_type, tags, title, chunk, hash_type, source_ref, vec),
                )

        print(f"Ingested {source_ref} -> {len(chunks)} chunks | tags={tags}")


if __name__ == "__main__":
    import sys
    # Usage:
    #   python -m services.rag.ingest_class_docs <CLASS_ID> /app/data/classes/<CLASS_ID>
    class_id = sys.argv[1]
    folder = Path(sys.argv[2])
    ingest_class_folder(class_id, folder)
