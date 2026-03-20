from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from qsa.config.settings import Settings
from qsa.execution.tws_client import TWS_Wrapper_Client
from qsa.schemas.artifacts import DatasetSnapshot
from qsa.schemas.data import Bar


REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "volume")


def _clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans an OHLCV (Open, High, Low, Close, Volume) DataFrame to ensure data integrity and proper formatting.

    Steps performed:
    1. Verifies that all required columns ("time", "open", "high", "low", "close", "volume") are present; raises ValueError if any are missing.
    2. Selects and copies only the required columns.
    3. Converts the "time" column to pandas datetime (without forcing UTC).
    4. Drops rows where any of "time", "open", "high", "low", or "close" are missing (NaN).
    5. Sorts by "time" column, removes duplicate time values, and resets the index.
    6. Converts all price and volume columns to float, coercing errors to NaN.
    7. Drops any rows that still have NaN in the price columns ("open", "high", "low", "close").
    8. Fills remaining NaN values in "volume" with 0.0.
    9. Returns the cleaned DataFrame.
    """
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Historical dataset missing required columns: {missing}")

    cleaned = df[list(REQUIRED_COLUMNS)].copy()
    cleaned["time"] = pd.to_datetime(cleaned["time"], utc=False)
    cleaned = cleaned.dropna(subset=["time", "open", "high", "low", "close"])
    cleaned = cleaned.sort_values("time").drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)

    for column in ("open", "high", "low", "close", "volume"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    cleaned = cleaned.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    cleaned["volume"] = cleaned["volume"].fillna(0.0)
    return cleaned


def _dataset_digest(cleaned: pd.DataFrame) -> str:
    """
    Generate a SHA-256 hash of the cleaned OHLCV DataFrame.
    """
    payload = cleaned.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _to_bars(cleaned: pd.DataFrame) -> list[Bar]:
    """
    Convert the cleaned OHLCV DataFrame to a list of Bar objects.
    """
    bars: list[Bar] = []
    for row in cleaned.itertuples(index=False):
        bars.append(
            Bar(
                time=row.time.to_pydatetime(),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
        )
    return bars


async def _fetch_ibkr_history(settings: Settings) -> pd.DataFrame:
    """
    Fetch historical data from IBKR and return a DataFrame.
    """
    client = TWS_Wrapper_Client(
        host=settings.ib_host,
        port=settings.ib_port,
        client_id=settings.ib_client_id,
        account=settings.ib_account,
    )
    await client.connect()
    try:
        contract = TWS_Wrapper_Client.get_contract(
            symbol=settings.ib_symbol,
            contract_id=settings.ib_contract_id,
            exchange=settings.ib_exchange,
        )
        await client.request_historical_data(
            contract=contract,
            duration=settings.ib_duration,
            bar_size=settings.ib_bar_size,
            what_to_show=settings.ib_what_to_show,
            use_rth=settings.ib_use_rth,
            keep_up_to_date=False,
        )
        ready = await client.wait_for_historical_data(settings.ib_symbol, settings.ib_bar_size, timeout_s=30.0)
        if not ready:
            raise TimeoutError("Timed out waiting for IBKR historical bars.")
        frame = client.get_ohlc_data(settings.ib_symbol, settings.ib_bar_size).reset_index(drop=True)
        if frame.empty:
            raise ValueError("IBKR historical request returned zero rows.")
        return frame
    finally:
        await client.disconnect()


def build_versioned_dataset(settings: Settings) -> DatasetSnapshot:
    """
    Retrieve, clean, and version historical OHLCV data from IBKR according to the provided settings.

    This function fetches historical bar data from IBKR, cleans and validates the data,
    generates a unique dataset ID (digest), and constructs a manifest describing the dataset.
    Returns a DatasetSnapshot containing the cleaned DataFrame, list of Bar objects, and manifest metadata.

    Raises:
        ValueError: If the data source is not 'ibkr', or if cleaning results in an empty DataFrame.
    """
    if settings.data_source != "ibkr":
        raise ValueError(f"Unsupported data source: {settings.data_source}. Expected 'ibkr'.")

    raw = asyncio.run(_fetch_ibkr_history(settings))
    cleaned = _clean_ohlcv(raw)
    if cleaned.empty:
        raise ValueError("No rows left after dataset cleaning.")

    dataset_id = _dataset_digest(cleaned)
    manifest = {
        "dataset_id": dataset_id,
        "created_at": datetime.now(UTC).isoformat(),
        "source": settings.data_source,
        "rows": int(len(cleaned)),
        "request": {
            "symbol": settings.ib_symbol,
            "contract_id": settings.ib_contract_id,
            "exchange": settings.ib_exchange,
            "duration": settings.ib_duration,
            "bar_size": settings.ib_bar_size,
            "what_to_show": settings.ib_what_to_show,
            "use_rth": settings.ib_use_rth,
        },
    }
    return DatasetSnapshot(
        dataset_id=dataset_id,
        bars_frame=cleaned,
        bars=_to_bars(cleaned),
        manifest=manifest,
    )


async def fetch_ibkr_bars_async(settings: Settings) -> list[Bar]:
    """
    Asynchronously fetch and process historical OHLCV data from IBKR according to the provided settings.

    Retrieves raw historical data, cleans and validates the resulting DataFrame, and converts
    it into a list of Bar objects. Raises a ValueError if the data source is not IBKR or if
    no rows remain after cleaning.

    Args:
        settings (Settings): Configuration specifying IBKR connection and data parameters.

    Returns:
        list[Bar]: List of cleaned and parsed Bar objects.
    """
    if settings.data_source != "ibkr":
        raise ValueError(f"Unsupported data source: {settings.data_source}. Expected 'ibkr'.")
    raw = await _fetch_ibkr_history(settings)
    cleaned = _clean_ohlcv(raw)
    if cleaned.empty:
        raise ValueError("No rows left after dataset cleaning.")
    return _to_bars(cleaned)


def fetch_ibkr_bars(settings: Settings) -> list[Bar]:
    """
    Synchronously fetch and process historical OHLCV data from IBKR.

    Runs the asynchronous IBKR data retrieval and cleaning logic, returning a list of
    Bar objects. This function blocks until the asynchronous task completes.

    Args:
        settings (Settings): Configuration specifying IBKR connection and data parameters.

    Returns:
        list[Bar]: List of cleaned and parsed Bar objects.
    """
    return asyncio.run(fetch_ibkr_bars_async(settings))
