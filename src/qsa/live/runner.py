from __future__ import annotations


def run_live(config_path: str, dry_run: bool) -> dict[str, str | bool]:
    return {
        "status": "ok",
        "mode": "live",
        "config": config_path,
        "dry_run": dry_run,
        "message": "Template scaffold: wire broker, data, and strategy for live execution.",
    }

