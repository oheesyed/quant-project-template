from __future__ import annotations


def run_backtest(config_path: str) -> dict[str, str]:
    return {
        "status": "ok",
        "mode": "backtest",
        "config": config_path,
        "message": "Template scaffold: implement your strategy and engine wiring.",
    }

