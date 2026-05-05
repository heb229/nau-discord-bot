# FOR POSTGRESS DB - RAG INTEGRATION

import os
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is required")

def _configure(conn):
    register_vector(conn)

pool = ConnectionPool(conninfo = DATABASE_URL, max_size = 10, configure = _configure)