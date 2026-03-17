from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, cast

import pandas as pd
from ib_async import Contract, IB, LimitOrder, MarketOrder, StopOrder


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class TWS_Wrapper_Client:
    """Async wrapper around ib_async with parity to the legacy TWS helper."""

    def __init__(
        self,
        host: str,
        port: int,
        client_id: int,
        ib_account: str | None = None,
        account: str | None = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.client_id = int(client_id)
        self.ib_account = str(ib_account or account or "")

        self.ib = IB()
        self.req_mkt_id = 1
        self.req_hist_data_id = 1
        self.req_mkt_map: dict[int, str] = {}
        self.req_hist_map: dict[int, dict[str, str]] = {}
        self.marketdata: dict[str, Any] = {}
        self.ohlc_data: dict[str, dict[str, dict[str, Any]]] = {}
        self._historical_subscriptions: dict[tuple[str, str], Any] = {}

    async def connect(self) -> None:
        await self.ib.connectAsync(
            host=self.host,
            port=self.port,
            clientId=self.client_id,
            account=self.ib_account,
        )
        await self.ib.reqAllOpenOrdersAsync()
        if self.client_id == 0:
            self.ib.reqAutoOpenOrders(True)
        await self.ib.reqExecutionsAsync()

    def get_managed_accounts(self) -> list[str]:
        raw_accounts = self.ib.managedAccounts()
        if raw_accounts is None:
            return []
        if isinstance(raw_accounts, str):
            return [acct.strip() for acct in raw_accounts.split(",") if acct.strip()]
        return [str(acct).strip() for acct in raw_accounts if str(acct).strip()]

    @staticmethod
    def get_contract(symbol: str, contract_id: int, exchange: str) -> Contract:
        kwargs: dict[str, Any] = {
            "symbol": str(symbol),
            "secType": "STK",
            "exchange": str(exchange),
            "currency": "USD",
        }
        if int(contract_id) > 0:
            kwargs["conId"] = int(contract_id)
        return Contract(**kwargs)

    async def request_market_data(
        self, contract: Contract, *, delayed: bool = False, req_id: int | None = None
    ) -> None:
        if delayed:
            self.ib.reqMarketDataType(3)
        if req_id is None:
            req_id = self.req_mkt_id
            self.req_mkt_id += 1

        symbol = str(getattr(contract, "localSymbol", None) or getattr(contract, "symbol", None) or req_id)
        self.req_mkt_map[int(req_id)] = symbol
        self.marketdata[symbol] = self.ib.reqMktData(contract)
        await asyncio.sleep(0.01)

    @staticmethod
    def _to_epoch_and_dt(raw: Any) -> tuple[int, datetime]:
        if isinstance(raw, datetime):
            return int(raw.timestamp()), raw
        if isinstance(raw, date):
            dt = datetime.combine(raw, datetime.min.time())
            return int(dt.timestamp()), dt

        normalized = str(raw).strip()
        if normalized.isdigit():
            if len(normalized) == 8:
                dt = datetime.strptime(normalized, "%Y%m%d")
                return int(dt.timestamp()), dt
            ts = int(normalized)
            return ts, datetime.fromtimestamp(ts)

        dt = datetime.strptime(" ".join(normalized.split()), "%Y%m%d %H:%M:%S")
        return int(dt.timestamp()), dt

    def _bars_to_df(self, bars: Any) -> pd.DataFrame:
        df = pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
        for bar in list(bars):
            time_key, time_dt = self._to_epoch_and_dt(getattr(bar, "date", ""))
            df.loc[time_key, ["time", "open", "high", "low", "close", "volume"]] = [
                time_dt,
                getattr(bar, "open", None),
                getattr(bar, "high", None),
                getattr(bar, "low", None),
                getattr(bar, "close", None),
                str(getattr(bar, "volume", "")),
            ]
        return df.sort_index()

    def _upsert_hist_data(self, symbol: str, timeframe: str, bars: Any) -> None:
        self.ohlc_data.setdefault(symbol, {})
        self.ohlc_data[symbol][timeframe] = {
            "data": self._bars_to_df(bars),
            "end": datetime.now(),
            "start_str": "",
            "end_str": "",
        }
        self._historical_subscriptions[(symbol, timeframe)] = bars

    async def request_historical_data(
        self,
        contract: Contract,
        duration: str,
        bar_size: str,
        *,
        what_to_show: str = "TRADES",
        use_rth: int = 1,
        keep_up_to_date: bool = False,
        req_id: int | None = None,
    ) -> None:
        if req_id is None:
            req_id = self.req_hist_data_id
            self.req_hist_data_id += 1

        symbol = str(getattr(contract, "localSymbol", None) or getattr(contract, "symbol", None) or req_id)
        timeframe = str(bar_size)
        self.req_hist_map[int(req_id)] = {"local_symbol": symbol, "timeframe": timeframe}

        bars = await self.ib.reqHistoricalDataAsync(
            contract=contract,
            endDateTime="",
            durationStr=str(duration),
            barSizeSetting=timeframe,
            whatToShow=str(what_to_show),
            useRTH=bool(use_rth),
            formatDate=1,
            keepUpToDate=bool(keep_up_to_date),
            chartOptions=[],
            timeout=30,
        )
        self._upsert_hist_data(symbol, timeframe, bars)

    def get_account_data(self) -> dict[str, float | None]:
        account_values = self.ib.accountValues(account=self.ib_account)
        account_balance: float | None = None
        account_equity: float | None = None
        maintenance_margin: float | None = None
        free_margin: float | None = None

        for item in account_values:
            key = str(getattr(item, "tag", ""))
            value = _safe_float(getattr(item, "value", None))
            currency = str(getattr(item, "currency", ""))

            if currency == "BASE" and key == "CashBalance":
                account_balance = value
            elif currency == "BASE" and key == "NetLiquidationByCurrency":
                account_equity = value
            elif key == "MaintMarginReq":
                maintenance_margin = value
            elif key == "ExcessLiquidity":
                free_margin = value

        return {
            "account_balance": account_balance,
            "account_equity": account_equity,
            "maintenance_margin": maintenance_margin,
            "free_margin": free_margin,
        }

    def get_positions(self) -> dict[str, dict[str, Any]]:
        positions: dict[str, dict[str, Any]] = {}
        for item in self.ib.portfolio(account=self.ib_account):
            symbol = str(
                getattr(getattr(item, "contract", None), "localSymbol", None)
                or getattr(getattr(item, "contract", None), "symbol", None)
                or ""
            )
            positions[symbol] = {
                "position": _safe_float(getattr(item, "position", 0)) or 0.0,
                "marketPrice": _safe_float(getattr(item, "marketPrice", None)),
                "marketValue": _safe_float(getattr(item, "marketValue", None)),
                "averageCost": _safe_float(getattr(item, "averageCost", None)),
                "unrealizedPNL": _safe_float(getattr(item, "unrealizedPNL", None)),
                "realizedPNL": _safe_float(getattr(item, "realizedPNL", None)),
            }
        return positions

    def _serialize_trade(self, trade: Any) -> dict[str, Any]:
        order = getattr(trade, "order", None)
        contract = getattr(trade, "contract", None)
        order_status = getattr(trade, "orderStatus", None)
        order_id = int(getattr(order, "orderId", 0))
        return {
            "local_symbol": str(getattr(contract, "localSymbol", None) or getattr(contract, "symbol", "")),
            "commission": _safe_float(getattr(order_status, "commission", None)),
            "commission_currency": getattr(order_status, "commissionCurrency", None),
            "completed_status": getattr(order_status, "completedStatus", None),
            "start_time": getattr(order, "activeStartTime", None),
            "action": getattr(order, "action", None),
            "order_type": getattr(order, "orderType", None),
            "quantity": str(getattr(order, "totalQuantity", "")),
            "tif": getattr(order, "tif", None),
            "lmt_price": _safe_float(getattr(order, "lmtPrice", None)),
            "aux_price": _safe_float(getattr(order, "auxPrice", None)),
            "status": getattr(order_status, "status", None),
            "has_been_filled": getattr(order_status, "status", "") == "Filled",
            "order_id": order_id,
        }

    def get_orders(self) -> dict[int, dict[str, Any]]:
        orders: dict[int, dict[str, Any]] = {}
        for trade in self.ib.trades():
            serialized = self._serialize_trade(trade)
            orders[int(serialized["order_id"])] = serialized
        return orders

    def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
        return self.get_orders().get(int(order_id))

    def get_market_data_price(self, symbol: str) -> dict[str, Any]:
        ticker = self.marketdata.get(symbol)
        if ticker is None:
            return {}
        return {
            "bid": _safe_float(getattr(ticker, "bid", None)),
            "ask": _safe_float(getattr(ticker, "ask", None)),
            "last": _safe_float(getattr(ticker, "last", None)),
            "bid_size": str(getattr(ticker, "bidSize", "")),
            "ask_size": str(getattr(ticker, "askSize", "")),
            "last_size": str(getattr(ticker, "lastSize", "")),
            "bid_time": getattr(ticker, "time", None),
            "ask_time": getattr(ticker, "time", None),
            "last_time": getattr(ticker, "time", None),
        }

    def get_trade_report(self) -> list[dict[str, Any]]:
        trade_report: list[dict[str, Any]] = []
        for fill in self.ib.fills():
            execution = getattr(fill, "execution", None)
            contract = getattr(fill, "contract", None)
            commission_report = getattr(fill, "commissionReport", None)
            trade_report.append(
                {
                    "symbol": str(getattr(contract, "localSymbol", None) or getattr(contract, "symbol", "")),
                    "time": getattr(execution, "time", None),
                    "account": getattr(execution, "acctNumber", None),
                    "action": getattr(execution, "side", None),
                    "quantity": _safe_float(getattr(execution, "shares", 0)) or 0.0,
                    "price": _safe_float(getattr(execution, "price", None)),
                    "commission": _safe_float(getattr(commission_report, "commission", None)),
                    "commission_currency": getattr(commission_report, "currency", None),
                }
            )
        return trade_report

    def get_position(self, symbol: str) -> float:
        return float(self.get_positions().get(symbol, {}).get("position", 0.0))

    def get_ohlc_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        subscription = self._historical_subscriptions.get((symbol, timeframe))
        if subscription is not None:
            self._upsert_hist_data(symbol, timeframe, subscription)
        return cast(pd.DataFrame, self.ohlc_data[symbol][timeframe]["data"])

    async def wait_for_historical_data(
        self, symbol: str, timeframe: str, *, timeout_s: float = 30.0, poll_s: float = 0.1
    ) -> bool:
        deadline = datetime.now() + timedelta(seconds=float(timeout_s))
        while datetime.now() < deadline:
            tf_data = self.ohlc_data.get(symbol, {}).get(timeframe)
            if tf_data and tf_data.get("end") and hasattr(tf_data.get("data"), "empty") and not tf_data["data"].empty:
                return True
            await asyncio.sleep(float(poll_s))
        return False

    async def send_market_order(
        self, contract: Contract, action: str, quantity: int, tif: str = "DAY"
    ) -> dict[str, int]:
        order = MarketOrder(action=str(action), totalQuantity=int(quantity), tif=str(tif))
        trade = self.ib.placeOrder(contract, order)
        await asyncio.sleep(0.01)
        return {"order_id": int(getattr(trade.order, "orderId", 0))}

    async def place_market_order(
        self,
        symbol: str,
        quantity: float,
        price_hint: float | None = None,
    ) -> str:
        del price_hint
        if abs(float(quantity)) < 1.0:
            raise ValueError(f"Market order quantity must be at least 1 share. Got {quantity:.4f}.")
        contract = self.get_contract(symbol=symbol, contract_id=0, exchange="SMART")
        action = "BUY" if quantity > 0 else "SELL"
        result = await self.send_market_order(
            contract=contract,
            action=action,
            quantity=abs(int(quantity)),
            tif="DAY",
        )
        order_id = int(result["order_id"])
        await asyncio.sleep(0.2)
        order = self.get_order_by_id(order_id)
        status = str(order.get("status", "") if order is not None else "")
        if status in {"ValidationError", "ApiCancelled", "Cancelled", "Inactive"}:
            raise RuntimeError(
                f"IBKR rejected market order {order_id} for {symbol}: status={status}."
            )
        return f"ibkr:{symbol}:{quantity:.4f}:{order_id}"

    async def send_limit_order(
        self,
        contract: Contract,
        action: str,
        quantity: int,
        limit_price: float,
        tif: str = "DAY",
        all_or_none: bool = True,
    ) -> dict[str, int]:
        order = LimitOrder(
            action=str(action),
            totalQuantity=int(quantity),
            lmtPrice=float(limit_price),
            tif=str(tif),
            allOrNone=bool(all_or_none),
        )
        trade = self.ib.placeOrder(contract, order)
        await asyncio.sleep(0.01)
        return {"order_id": int(getattr(trade.order, "orderId", 0))}

    async def send_stop_order(
        self,
        contract: Contract,
        action: str,
        quantity: int,
        stop_price: float,
        tif: str = "DAY",
        all_or_none: bool = True,
    ) -> dict[str, int]:
        order = StopOrder(
            action=str(action),
            totalQuantity=int(quantity),
            stopPrice=float(stop_price),
            tif=str(tif),
            allOrNone=bool(all_or_none),
        )
        trade = self.ib.placeOrder(contract, order)
        await asyncio.sleep(0.01)
        return {"order_id": int(getattr(trade.order, "orderId", 0))}

    def cancel_order(self, order_id: int) -> dict[str, int]:
        trade = self.get_order_by_id(int(order_id))
        if trade is None:
            return {"order_id": int(order_id)}
        order = next((t.order for t in self.ib.trades() if int(getattr(t.order, "orderId", -1)) == int(order_id)), None)
        if order is not None:
            self.ib.cancelOrder(order)
        return {"order_id": int(order_id)}

    async def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()

