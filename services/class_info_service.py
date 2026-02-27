# imports
import json
from pathlib import Path

# class to provide class information based on specificed class
    # looks at selected class and pulls informaiton from its json
class ClassInfoService:
    def __init__(self, guild_id: int):
        self.file_path = Path(f"data/classes/{guild_id}/{guild_id}.json")

    def exists(self) -> bool:
        return self.file_path.exists()

    def load(self) -> dict | None:
        if not self.exists():
            return None

        with open(self.file_path, "r", encoding = "utf-8") as f:
            return json.load(f)

    def save(self, data: dict):
        self.file_path.parent.mkdir(parents = True, exist_ok = True)

        with open(self.file_path, "w", encoding = "utf-8") as f:
            json.dump(data, f, indent=4)
