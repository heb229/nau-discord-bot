# Services Structure

This folder contains the non-command backend logic for the Discord bot.


## Current Layout

### `services/ai/`

This folder contains AI engine selection and model-specific implementations.

- `selector.py`
  Central place to choose which response engine and embedding engine the app uses.
  If you want to swap models later, this is the main file to edit.

- `model_engine.py`
  Base classes and concrete engine implementations.
  Right now it includes:
  - `ResponseEngine`
  - `EmbeddingEngine`
  - `GeminiEngine`
  - `GeminiEmbeddingEngine`

- `__init__.py`
  Re-exports the selector helpers.


### `services/chatbot/`

This folder contains chatbot-specific behavior that sits below the Discord cog.

- `guard.py`
  Academic-integrity restriction checks and cleanup logic.

- `responder.py`
  Builds the prompt and calls the selected response engine.

- `settings.py`
  Loads and saves runtime chatbot settings from `data/bot_settings.json`.

- `__init__.py`
  Re-exports chatbot helpers.


### `services/rag/`

This folder contains retrieval and ingestion logic for database-backed context.

- `retriever.py`
  Retrieves class context and thread context from Postgres/pgvector.

- `ingest_class_docs.py`
  Loads `.txt` class files, chunks them, embeds them, and stores them in `class_docs`.


## Other Top-Level Service Files

- `db.py`
  Postgres connection pool setup.

- `class_info_service.py`
  Reads and writes per-class JSON info used by `/info` and `/class`.

- `class_context.py`
  Older file-based class context helper. Still present, but the main chatbot flow now uses DB-backed retrieval.

- `roster_service.py`
  Reads the roster spreadsheet for student verification.

- `name_service.py`
  Small helper for formatting names during verification.

- `schema.sql`
  Database schema used by Docker/Postgres initialization.


## Design Intent

The goal of this structure is:

- keep Discord command code in `commands/`
- keep AI model selection centralized in one place
- keep chatbot behavior separate from model implementation details
- keep retrieval/ingestion logic separate from Discord interaction logic


## If You Want To Swap AI Engines Later

The main place to change is:

`services/ai/selector.py`

You should only need to change the selected classes there, as long as the new engine follows the `ResponseEngine` and `EmbeddingEngine` interfaces defined in `services/ai/model_engine.py`.
