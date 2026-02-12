from __future__ import annotations

from datetime import datetime
from time import sleep

import pandas as pd

from brokers.base import OrderSide
from brokers.ibkr import IBKRBroker, IBKRSettings
from config.settings import Settings
from strategies.momentum_example import MomentumParams, decide_target_position


def _position_for_symbol(positions: dict, symbol: str) -> int:
    pos = positions.get(symbol, {}).get("position", 0)
    try:
        return int(pos)
    except Exception:
        return 0


def main() -> None:
    s = Settings()

    symbol = "ASML"
    contract_id = 117902840
    exchange = "NASDAQ"

    bar_size = "1 min"
    duration = "1 D"

    p = MomentumParams(lookback=15, entry_th=0.05, qty=100)

    broker = IBKRBroker(
        IBKRSettings(
            host=s.ibkr_host,
            port=s.ibkr_port,
            client_id=s.ibkr_client_id,
            account=s.ibkr_account,
        )
    )

    broker.connect()
    try:
        contract = broker.get_contract(symbol=symbol, contract_id=contract_id, exchange=exchange)

        broker.request_market_data(symbol=symbol, contract=contract, delayed=False)
        broker.request_historical_data(
            symbol=symbol,
            contract=contract,
            duration=duration,
            bar_size=bar_size,
            keep_up_to_date=True,
            use_rth=0,
        )

        ready = broker.wait_for_historical_data(symbol=symbol, bar_size=bar_size, timeout_s=60)
        if not ready:
            raise TimeoutError(f"Timed out waiting for historical data: {symbol} {bar_size}")

        internal_exposure = _position_for_symbol(broker.get_positions(), symbol)

        while True:
            acct = broker.get_account()
            positions = broker.get_positions()
            exposure = _position_for_symbol(positions, symbol)

            md = broker.get_market_data(symbol=symbol)
            ohlc = broker.get_ohlc(symbol=symbol, bar_size=bar_size)

            if not pd.api.types.is_datetime64_any_dtype(ohlc["time"]):
                ohlc = ohlc.copy()
                ohlc["time"] = pd.to_datetime(ohlc["time"])

            last_candle_time = ohlc.iloc[-1]["time"]
            time_difference = datetime.now() - last_candle_time.to_pydatetime()
            print(f"Time difference: {time_difference}  last={last_candle_time}  md={md}")

            if internal_exposure != exposure:
                raise RuntimeError("Exposure discrepancy detected (internal vs broker).")

            target = decide_target_position(ohlc, position=exposure, p=p)
            delta = int(target - exposure)

            if delta > 0:
                broker.send_market_order(contract=contract, side=OrderSide.BUY, quantity=abs(delta))
                internal_exposure += abs(delta)
                sleep(1)
            elif delta < 0:
                broker.send_market_order(contract=contract, side=OrderSide.SELL, quantity=abs(delta))
                internal_exposure -= abs(delta)
                sleep(1)

            print(
                f"cash={acct.account_balance} equity={acct.account_equity} exposure={exposure} target={target} delta={delta}"
            )
            sleep(1)

    finally:
        broker.disconnect()


if __name__ == "__main__":
    main()
