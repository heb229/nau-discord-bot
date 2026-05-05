import os
from abc import ABC, abstractmethod

import requests
from dotenv import load_dotenv
from google import genai

# load in env file for API keys and such
load_dotenv()

# ---------- MODEL ENGINES ----------

class ResponseEngine(ABC):
    """
    Base class for text-generation engines.
    """

    # abstract method to generate a response for a given prompt. Subclasses must implement this method.
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a plain-text response for a prompt.
        """
        raise NotImplementedError


# ResponseEngine and EmbeddingEngine are separate because some LLM providers (like Google) 
# have different endpoints/models for text generation and embeddings. This allows us to mix 
# and match as needed.

# ResponseEngine is for generating text responses to user questions, while EmbeddingEngine 
# is for generating vector embeddings of text (for RAG retrieval).
class EmbeddingEngine(ABC):
    """
    Base class for embedding engines.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embedding vectors for a batch of strings.
        """
        raise NotImplementedError


# ------------- ENGINE IMPLEMENTATIONS -------------

# GeminiEngine is a ResponseEngine implementation that uses the Google AI Studio API to 
# generate responses.
class GeminiEngine(ResponseEngine):
    """
    Gemini-based response engine using Google AI Studio API.
    """

    # initialize the Gemini client with the provided API key and model name. 
    # If no model is provided, it defaults to "gemini-3-flash-preview".
    def __init__(self, model: str | None = None):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    # generate a response for the given prompt using the Gemini model. It sends a request to the 
    # Google API and returns the generated text. If no text is returned, it raises an error.
    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        text = response.text
        if text is None:
            raise RuntimeError("Gemini returned no text response.")
        return text.strip()


# GeminiEmbeddingEngine is an EmbeddingEngine implementation that uses the Google AI Studio API to 
# generate embeddings for a list of input texts. It sends a request to the embedding endpoint and 
# returns a list of embedding vectors corresponding to the input texts. If the API call fails, 
# it raises an error.
class GeminiEmbeddingEngine(EmbeddingEngine):
    """
    Gemini embeddings client using HTTP.
    """

    # initialize the Gemini embedding engine with the provided API key and model name
    def __init__(self, model: str | None = None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Ensure the API key is available; if not, raise an error immediately to avoid 
        # silent failures later.
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required")
        self.model = model or os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

    # generate embedding vectors for a list of input texts by sending a POST request to the 
    # Gemini embedding endpoint.
    def embed(self, texts: list[str]) -> list[list[float]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent"
        out: list[list[float]] = []

        # The Gemini embedding API expects a batch of texts in the "content.parts.text" field. 
        # We loop through each text, send it to the API, and collect the resulting embedding vectors. 
        # If any API call fails, an exception will be raised, which should be handled by the caller.
        for text in texts:
            payload = {"content": {"parts": [{"text": text}]}}
            response = requests.post(url, params={"key": self.api_key}, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            out.append(data["embedding"]["values"])

        return out
