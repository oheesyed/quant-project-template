from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import yaml

from qsa.backtest.run import run_backtest
from qsa.cli import _build_parser
from qsa.data import pipeline as data_pipeline
from qsa.live import runner
from qsa.schemas.data import Bar
from qsa.strategies.base import StrategySignal


class _FakeBroker:
    def __init__(self, host: str, port: int, client_id: int, account: str) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account = account

    @staticmethod
    def get_contract(symbol: str, contract_id: int, exchange: str) -> dict[str, object]:
        return {"symbol": symbol, "contract_id": contract_id, "exchange": exchange}

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def request_historical_data(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        return None

    async def wait_for_historical_data(
        self, symbol: str, timeframe: str, timeout_s: float = 30.0
    ) -> bool:
        del symbol, timeframe, timeout_s
        return True

    def get_ohlc_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        del symbol, timeframe
        start = datetime(2025, 1, 1)
        rows: list[dict[str, object]] = []
        for idx in range(30):
            close = 100 + idx
            rows.append(
                {
                    "time": start + timedelta(days=idx),
                    "open": close - 0.2,
                    "high": close + 0.5,
                    "low": close - 0.6,
                    "close": close,
                    "volume": 1_000 + idx,
                }
            )
        return pd.DataFrame(rows)

    def get_position(self, symbol: str) -> float:
        del symbol
        return 0.0

    def get_managed_accounts(self) -> list[str]:
        return [self.account]

    def get_account_data(self) -> dict[str, float | None]:
        return {
            "account_balance": 100_000.0,
            "account_equity": 100_000.0,
            "maintenance_margin": 0.0,
            "free_margin": 100_000.0,
        }

    async def place_market_order(
        self,
        symbol: str,
        quantity: float,
        price_hint: float | None = None,
    ) -> str:
        del symbol, quantity, price_hint
        return "fake-order-id"


class _NoEquityBroker(_FakeBroker):
    def get_account_data(self) -> dict[str, float | None]:
        return {
            "account_balance": 100_000.0,
            "account_equity": None,
            "maintenance_margin": 0.0,
            "free_margin": 100_000.0,
        }


class _RejectingBroker(_FakeBroker):
    async def place_market_order(
        self,
        symbol: str,
        quantity: float,
        price_hint: float | None = None,
    ) -> str:
        del symbol, quantity, price_hint
        raise RuntimeError("IBKR rejected market order 4 for TEST: status=ValidationError.")


class _UnknownAccountBroker(_FakeBroker):
    def get_managed_accounts(self) -> list[str]:
        return ["DU9999999"]


class _NoManagedAccountsBroker(_FakeBroker):
    def get_managed_accounts(self) -> list[str]:
        return []


class _SymbolRecordingBroker(_FakeBroker):
    requested_contract_symbols: list[str] = []
    position_symbols: list[str] = []

    @staticmethod
    def get_contract(symbol: str, contract_id: int, exchange: str) -> dict[str, object]:
        _SymbolRecordingBroker.requested_contract_symbols.append(symbol)
        return {"symbol": symbol, "contract_id": contract_id, "exchange": exchange}

    def get_position(self, symbol: str) -> float:
        self.position_symbols.append(symbol)
        return 0.0


class _RecordingStrategy:
    seen_lengths: list[int] = []
    seen_last_closes: list[float] = []

    def __init__(self, params: object) -> None:
        del params

    def generate_signal(self, bars: list[Bar], current_position: float) -> StrategySignal:
        del current_position
        self.seen_lengths.append(len(bars))
        self.seen_last_closes.append(bars[-1].close)
        return StrategySignal(target_position=0.0, action="recorded")


def _write_isolated_config(tmp_path: Path, template_path: str) -> str:
    template = Path(template_path)
    cfg = yaml.safe_load(template.read_text())
    data_root = tmp_path / "data"
    cfg["data"]["root"] = str(data_root)
    out_path = tmp_path / template.name
    out_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return str(out_path)


def test_backtest_returns_mode_and_metrics(tmp_path: Path) -> None:
    data_pipeline.TWS_Wrapper_Client = _FakeBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/dev.yaml")
    result = run_backtest(config_path=config_path)
    assert result["run_type"] == "backtest"
    assert "total_return" in result
    assert "plot_files" not in result


def test_live_dry_run_returns_mode(tmp_path: Path) -> None:
    runner.TWS_Wrapper_Client = _FakeBroker
    data_pipeline.TWS_Wrapper_Client = _FakeBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")
    result = asyncio.run(
        runner.run_live(config_path=config_path, dry_run=True, symbol="AAPL")
    )
    assert result.run_type == "live"
    assert result.order_id == "dry-run"
    serialized = asdict(result)
    assert serialized["signal_action"] == result.signal_action
    assert serialized["run_type"] == "live"


def test_live_defaults_to_configured_data_symbol(tmp_path: Path) -> None:
    runner.TWS_Wrapper_Client = _SymbolRecordingBroker
    data_pipeline.TWS_Wrapper_Client = _SymbolRecordingBroker  # type: ignore[assignment]
    _SymbolRecordingBroker.requested_contract_symbols = []
    _SymbolRecordingBroker.position_symbols = []
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")

    result = asyncio.run(runner.run_live(config_path=config_path, dry_run=True))

    assert result.symbol == "AAPL"
    assert _SymbolRecordingBroker.requested_contract_symbols == ["AAPL"]
    assert _SymbolRecordingBroker.position_symbols == ["AAPL"]


def test_live_rejects_symbol_that_differs_from_data_symbol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail_if_fetch_called(settings: object) -> list[Bar]:
        del settings
        raise AssertionError("live runner fetched data before validating symbol mismatch")

    monkeypatch.setattr(runner, "fetch_ibkr_bars_async", fail_if_fetch_called)
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")

    with pytest.raises(ValueError, match="must match data.ib_symbol"):
        asyncio.run(runner.run_live(config_path=config_path, dry_run=True, symbol="MSFT"))


def test_live_signal_excludes_execution_bar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = datetime(2025, 1, 1)
    bars = [
        Bar(
            time=start + timedelta(days=idx),
            open=float(close),
            high=float(close),
            low=float(close),
            close=float(close),
            volume=1_000.0,
        )
        for idx, close in enumerate([100, 110, 120, 500])
    ]

    async def fake_fetch(settings: object) -> list[Bar]:
        del settings
        return bars

    _RecordingStrategy.seen_lengths = []
    _RecordingStrategy.seen_last_closes = []
    monkeypatch.setattr(runner, "fetch_ibkr_bars_async", fake_fetch)
    monkeypatch.setattr(runner, "TWS_Wrapper_Client", _FakeBroker)
    monkeypatch.setattr(runner, "MomentumExampleStrategy", _RecordingStrategy)
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")

    result = asyncio.run(runner.run_live(config_path=config_path, dry_run=True))

    assert result.signal_action == "recorded"
    assert _RecordingStrategy.seen_lengths == [len(bars) - 1]
    assert _RecordingStrategy.seen_last_closes == [120.0]


def test_cli_live_accepts_symbol_argument() -> None:
    parser = _build_parser()
    args = parser.parse_args(
        ["live", "--config", "configs/paper.yaml", "--symbol", "AAPL"]
    )
    assert args.command == "live"
    assert args.symbol == "AAPL"


def test_live_non_dry_run_requires_account_equity(tmp_path: Path) -> None:
    runner.TWS_Wrapper_Client = _NoEquityBroker
    data_pipeline.TWS_Wrapper_Client = _NoEquityBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")
    with pytest.raises(RuntimeError, match="account_equity"):
        asyncio.run(runner.run_live(config_path=config_path, dry_run=False, symbol="AAPL"))


def test_live_non_dry_run_validates_configured_account(tmp_path: Path) -> None:
    runner.TWS_Wrapper_Client = _UnknownAccountBroker
    data_pipeline.TWS_Wrapper_Client = _UnknownAccountBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")
    with pytest.raises(RuntimeError, match="not in managed accounts"):
        asyncio.run(runner.run_live(config_path=config_path, dry_run=False, symbol="AAPL"))


def test_live_non_dry_run_requires_managed_account_list(tmp_path: Path) -> None:
    runner.TWS_Wrapper_Client = _NoManagedAccountsBroker
    data_pipeline.TWS_Wrapper_Client = _NoManagedAccountsBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")
    with pytest.raises(RuntimeError, match="returned no managed accounts"):
        asyncio.run(runner.run_live(config_path=config_path, dry_run=False, symbol="AAPL"))


def test_live_non_dry_run_surfaces_order_rejection(tmp_path: Path) -> None:
    runner.TWS_Wrapper_Client = _RejectingBroker
    data_pipeline.TWS_Wrapper_Client = _RejectingBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/paper.yaml")
    with pytest.raises(RuntimeError, match="IBKR rejected market order"):
        asyncio.run(runner.run_live(config_path=config_path, dry_run=False, symbol="AAPL"))
