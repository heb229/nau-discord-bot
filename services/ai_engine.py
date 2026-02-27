
# This file is used to demonstrate the requirements
# for future AI engine files. Essentially, if swapping
# from one LLM model to another, a new python script with
# the following must be implemented.

from abc import ABC, abstractmethod

class AIEngine(ABC):
    """
    Abstract interface for an AI engine.
    Any LLM backend must implement this.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a response from a prompt.
        Must return plain text.
        """
        pass
