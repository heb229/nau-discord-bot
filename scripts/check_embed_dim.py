# this is a test script in order to calculate the embedding dimension of the currently used model.
# if you wish to test a different embedding model, simply change the import statement to import the desired model's embed engine, 
# and ensure that the embed engine is properly initialized in the code below.

from services.gemini_embed_engine import GeminiEmbedEngine

if __name__ == "__main__":
    # engine tested
    e = GeminiEmbedEngine()
    # vector for test string
    v = e.embed(["hello world"])[0]
    # length of vector is the embedding dimension, which is what we want to check
    print("Embedding dimension:", len(v))