from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from qsa.schemas.data import Bar


@dataclass(frozen=True)
class DatasetSnapshot:
    dataset_id: str
    bars_frame: pd.DataFrame
    bars: list[Bar]
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path

