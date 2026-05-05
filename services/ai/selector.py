from services.ai.model_engine import GeminiEmbeddingEngine, GeminiEngine


# Change these two lines when swapping to a different AI provider/model implementation.
RESPONSE_ENGINE_CLASS = GeminiEngine
EMBEDDING_ENGINE_CLASS = GeminiEmbeddingEngine

# Factory functions to get instances of the response and embedding engines. 
# This allows us to centralize the choice of AI model implementations in one place,
# and easily swap them out if needed.
def get_response_engine():
    return RESPONSE_ENGINE_CLASS()


# For the embedding engine, we want to use a single shared instance across the application,
# since it may maintain internal state or connection pools. For the response engine, we can
# create new instances as needed since they are typically stateless.
def get_embedding_engine():
    return EMBEDDING_ENGINE_CLASS()
