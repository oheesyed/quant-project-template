from __future__ import annotations

from datetime import datetime, timezone


def new_run_id(*, prefix: str = "run") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{ts}"

