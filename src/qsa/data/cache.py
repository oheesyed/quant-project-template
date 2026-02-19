from __future__ import annotations

from pathlib import Path


class LocalCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def exists(self, key: str) -> bool:
        return (self.root / f"{key}.json").exists()

