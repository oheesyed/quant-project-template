from __future__ import annotations

import pandas as pd
from pathlib import Path


class LocalCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def exists(self, key: str) -> bool:
        return (self.root / f"{key}.csv").exists()

    def write_frame(self, key: str, df: pd.DataFrame) -> None:
        df.to_csv(self.root / f"{key}.csv", index=False)

    def read_frame(self, key: str) -> pd.DataFrame:
        path = self.root / f"{key}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Cache key not found: {key}")
        return pd.read_csv(path)

