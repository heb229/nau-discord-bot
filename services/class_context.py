# services/class_context.py
from pathlib import Path


# This ClassContext class is responsible for managing the context information related to a 
# specific class or course.
class ClassContext:
    def __init__(self, guild_id: int):
        self.base_path = Path(f"data/classes/{guild_id}")

    def list_contexts(self) -> dict[str, Path]:
        """
        Returns a mapping of display names -> file paths
        """
        contexts = {}

        general = self.base_path / "general.txt"
        if general.exists():
            contexts["General Class Info"] = general

        # we look for .txt files in the "concepts" and "projects" subfolders, and we create 
        # display names based on the folder and filename. For example, a file at 
        # "concepts/linked_lists.txt" would have a display name of "Concepts: Linked Lists".
        for folder in ["concepts", "projects"]:
            dir_path = self.base_path / folder
            if not dir_path.exists():
                continue

            for file in dir_path.glob("*.txt"):
                name = file.stem.replace("_", " ").title()
                contexts[f"{folder.title()}: {name}"] = file

        return contexts

    # This method loads the content of a context file given its path. 
    # It reads the text from the file and returns it as a string.
    def load_context(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")[:8000]
