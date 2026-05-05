-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- =========================
-- Core identity tables
-- =========================

CREATE TABLE IF NOT EXISTS users (
  user_id            TEXT PRIMARY KEY,      -- Discord user id
  preferred_name     TEXT,
  year               TEXT,
  on_campus_research BOOLEAN,
  taken_classes      TEXT[] DEFAULT '{}',
  is_active          BOOLEAN NOT NULL DEFAULT true,  -- soft-delete/graduation flag
  created_at         TIMESTAMPTZ DEFAULT now(),
  updated_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS classes (
  class_id   TEXT PRIMARY KEY,              -- Discord server id
  name       TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS threads (
  thread_id  TEXT PRIMARY KEY,              -- Discord thread id
  class_id   TEXT REFERENCES classes(class_id) ON DELETE SET NULL,
  title      TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS thread_participants (
  thread_id    TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
  user_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  joined_at    TIMESTAMPTZ DEFAULT now(),
  last_seen_at TIMESTAMPTZ,
  PRIMARY KEY (thread_id, user_id)
);

-- =========================
-- Class context docs (replaces your folder tree)
-- doc_type: concept | project | worksheet | rubric | general | misc
-- tags: Discord thread tags you use for filtering
-- =========================

CREATE TABLE IF NOT EXISTS class_docs (
  id           BIGSERIAL PRIMARY KEY,
  class_id     TEXT NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
  doc_type     TEXT NOT NULL,
  tags         TEXT[] DEFAULT '{}',
  title        TEXT,
  content      TEXT NOT NULL,
  content_hash TEXT,
  source_ref   TEXT,  -- optional: old filepath
  updated_at   TIMESTAMPTZ DEFAULT now(),
  embedding    vector(3072)
);

CREATE INDEX IF NOT EXISTS class_docs_class_idx ON class_docs(class_id);
CREATE INDEX IF NOT EXISTS class_docs_tags_gin ON class_docs USING GIN(tags);

-- HNSW index using half-precision expression so >2000 dims is supported
-- Note: this indexes the expression (embedding::halfvec(3072)), while storing full vector(3072)
CREATE INDEX IF NOT EXISTS class_docs_embedding_hnsw_half
  ON class_docs
  USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops);

-- =========================
-- Thread memory (shared conversation context)
-- mem_type: summary | decision | fact | open_question | message_chunk
-- =========================

CREATE TABLE IF NOT EXISTS thread_memory (
  id         BIGSERIAL PRIMARY KEY,
  thread_id  TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
  class_id   TEXT REFERENCES classes(class_id) ON DELETE SET NULL,
  mem_type   TEXT NOT NULL,
  author_id  TEXT REFERENCES users(user_id) ON DELETE SET NULL,
  content    TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  embedding  vector(3072)
);

CREATE INDEX IF NOT EXISTS thread_memory_thread_idx ON thread_memory(thread_id, created_at DESC);

CREATE INDEX IF NOT EXISTS thread_memory_embedding_hnsw_half
  ON thread_memory
  USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops);

-- =========================
-- User memory (private by default)
-- visibility: private | thread | class | public
-- mem_type: preference | strength | weakness | overview | background | recent_work
-- =========================

CREATE TABLE IF NOT EXISTS user_memory (
  id         BIGSERIAL PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  visibility TEXT NOT NULL DEFAULT 'private',
  mem_type   TEXT NOT NULL,
  content    TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now(),
  embedding  vector(3072)
);

CREATE INDEX IF NOT EXISTS user_memory_user_idx ON user_memory(user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS user_memory_embedding_hnsw_half
  ON user_memory
  USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops);

-- =========================
-- User conversation summaries ("table of summaries")
-- Each row = one session/episode summary
-- =========================

CREATE TABLE IF NOT EXISTS user_conversation_summaries (
  id         BIGSERIAL PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  class_id   TEXT REFERENCES classes(class_id) ON DELETE SET NULL,
  thread_id  TEXT REFERENCES threads(thread_id) ON DELETE SET NULL,
  summary    TEXT NOT NULL,
  key_points TEXT[] DEFAULT '{}',
  topics     TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  embedding  vector(3072)
);

CREATE INDEX IF NOT EXISTS ucs_user_created_idx ON user_conversation_summaries(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ucs_topics_gin ON user_conversation_summaries USING GIN(topics);

CREATE INDEX IF NOT EXISTS ucs_embedding_hnsw_half
  ON user_conversation_summaries
  USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops);


-- below is ORIGINAL. Will need to swap back for ANN, but doesnt work for current gemini dimension model.

-- -- Enable pgvector
-- CREATE EXTENSION IF NOT EXISTS vector;

-- -- =========================
-- -- Core identity tables
-- -- =========================

-- CREATE TABLE IF NOT EXISTS users (
--   user_id            TEXT PRIMARY KEY,      -- Discord user id
--   preferred_name     TEXT,
--   year               TEXT,
--   on_campus_research BOOLEAN,
--   taken_classes      TEXT[] DEFAULT '{}',
--   is_active          BOOLEAN NOT NULL DEFAULT true,  -- soft-delete/graduation flag
--   created_at         TIMESTAMPTZ DEFAULT now(),
--   updated_at         TIMESTAMPTZ DEFAULT now()
-- );

-- CREATE TABLE IF NOT EXISTS classes (
--   class_id   TEXT PRIMARY KEY,              -- Discord server id
--   name       TEXT,
--   created_at TIMESTAMPTZ DEFAULT now()
-- );

-- CREATE TABLE IF NOT EXISTS threads (
--   thread_id  TEXT PRIMARY KEY,              -- Discord thread id
--   class_id   TEXT REFERENCES classes(class_id) ON DELETE SET NULL,
--   title      TEXT,
--   created_at TIMESTAMPTZ DEFAULT now()
-- );

-- CREATE TABLE IF NOT EXISTS thread_participants (
--   thread_id    TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
--   user_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
--   joined_at    TIMESTAMPTZ DEFAULT now(),
--   last_seen_at TIMESTAMPTZ,
--   PRIMARY KEY (thread_id, user_id)
-- );

-- -- =========================
-- -- Class context docs (replaces your folder tree)
-- -- doc_type: concept | project | worksheet | rubric | general | misc
-- -- tags: Discord thread tags you use for filtering
-- -- =========================

-- CREATE TABLE IF NOT EXISTS class_docs (
--   id           BIGSERIAL PRIMARY KEY,
--   class_id     TEXT NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
--   doc_type     TEXT NOT NULL,
--   tags         TEXT[] DEFAULT '{}',
--   title        TEXT,
--   content      TEXT NOT NULL,
--   content_hash TEXT,
--   source_ref   TEXT,  -- optional: old filepath
--   updated_at   TIMESTAMPTZ DEFAULT now(),
--   embedding    vector(3072)
-- );

-- CREATE INDEX IF NOT EXISTS class_docs_class_idx ON class_docs(class_id);
-- CREATE INDEX IF NOT EXISTS class_docs_tags_gin ON class_docs USING GIN(tags);
-- CREATE INDEX IF NOT EXISTS class_docs_embedding_ivf
--   ON class_docs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- -- =========================
-- -- Thread memory (shared conversation context)
-- -- mem_type: summary | decision | fact | open_question | message_chunk
-- -- =========================

-- CREATE TABLE IF NOT EXISTS thread_memory (
--   id         BIGSERIAL PRIMARY KEY,
--   thread_id  TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
--   class_id   TEXT REFERENCES classes(class_id) ON DELETE SET NULL,
--   mem_type   TEXT NOT NULL,
--   author_id  TEXT REFERENCES users(user_id) ON DELETE SET NULL,
--   content    TEXT NOT NULL,
--   created_at TIMESTAMPTZ DEFAULT now(),
--   embedding  vector(3072)
-- );

-- CREATE INDEX IF NOT EXISTS thread_memory_thread_idx ON thread_memory(thread_id, created_at DESC);
-- CREATE INDEX IF NOT EXISTS thread_memory_embedding_ivf
--   ON thread_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- -- =========================
-- -- User memory (private by default)
-- -- visibility: private | thread | class | public
-- -- mem_type: preference | strength | weakness | overview | background | recent_work
-- -- =========================

-- CREATE TABLE IF NOT EXISTS user_memory (
--   id         BIGSERIAL PRIMARY KEY,
--   user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
--   visibility TEXT NOT NULL DEFAULT 'private',
--   mem_type   TEXT NOT NULL,
--   content    TEXT NOT NULL,
--   updated_at TIMESTAMPTZ DEFAULT now(),
--   embedding  vector(3072)
-- );

-- CREATE INDEX IF NOT EXISTS user_memory_user_idx ON user_memory(user_id, updated_at DESC);
-- CREATE INDEX IF NOT EXISTS user_memory_embedding_ivf
--   ON user_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- -- =========================
-- -- User conversation summaries ("table of summaries")
-- -- Each row = one session/episode summary
-- -- =========================

-- CREATE TABLE IF NOT EXISTS user_conversation_summaries (
--   id         BIGSERIAL PRIMARY KEY,
--   user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
--   class_id   TEXT REFERENCES classes(class_id) ON DELETE SET NULL,
--   thread_id  TEXT REFERENCES threads(thread_id) ON DELETE SET NULL,
--   summary    TEXT NOT NULL,
--   key_points TEXT[] DEFAULT '{}',
--   topics     TEXT[] DEFAULT '{}',
--   created_at TIMESTAMPTZ DEFAULT now(),
--   embedding  vector(3072)
-- );

-- CREATE INDEX IF NOT EXISTS ucs_user_created_idx ON user_conversation_summaries(user_id, created_at DESC);
-- CREATE INDEX IF NOT EXISTS ucs_topics_gin ON user_conversation_summaries USING GIN(topics);
-- CREATE INDEX IF NOT EXISTS ucs_embedding_ivf
--   ON user_conversation_summaries USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);