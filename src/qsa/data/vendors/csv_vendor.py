from __future__ import annotations

from pathlib import Path

import pandas as pd

from qsa.data.schemas import Bar


class CsvDataClient:
    def load_bars(self, csv_path: Path) -> list[Bar]:
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        df = pd.read_csv(csv_path)
        required = {"time", "open", "high", "low", "close", "volume"}
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        df["time"] = pd.to_datetime(df["time"], utc=False)
        df = df.sort_values("time").reset_index(drop=True)
        bars: list[Bar] = []
        for _, row in df.iterrows():
            bars.append(
                Bar(
                    time=row["time"].to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        return bars

