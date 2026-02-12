from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from threading import Thread
from time import sleep
from typing import Any

import pandas as pd
from ibapi.client import EClient
from ibapi.commission_report import CommissionReport
from ibapi.common import BarData, OrderId, TickAttrib, TickerId
from ibapi.contract import Contract
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.ticktype import TickType
from ibapi.wrapper import EWrapper


def decimalMaxString(val: Any) -> str:
    """Convert Decimal-like to string (replacement for missing ibapi.utils.decimalMaxString)."""
    return str(val) if val is not None else ""


class TradeApp(EWrapper, EClient):
    def __init__(self) -> None:
        EClient.__init__(self, self)

        self.next_order_id: int | None = None
        self.req_mkt_id = 1
        self.req_hist_data_id = 1

        # Request Market Data ID Map
        self.req_mkt_map: dict[int, str] = {}
        self.marketdata: dict[str, dict[str, Any]] = {}

        # Request Historical Data ID Map
        self.req_hist_map: dict[int, dict[str, str]] = {}
        self.ohlc_data: dict[str, dict[str, dict[str, Any]]] = {}

        # Account Data
        self.account_balance: float | None = None
        self.account_equity: float | None = None
        self.free_margin: float | None = None
        self.maintenance_margin: float | None = None
        # Ex: {"AAPL": {"position": 100, "marketPrice": 150, ...}}
        self.portfolio: dict[str, dict[str, Any]] = {}
        self.orders: dict[int, dict[str, Any]] = {}

        self.executions: dict[str, dict[str, Any]] = {}
        self.commission_report: dict[str, dict[str, Any]] = {}

    # ---- Internal helpers (non-EWrapper callbacks) ----
    def _get_next_valid_id(self) -> int:
        if self.next_order_id is None:
            raise RuntimeError("next_order_id not set yet (waiting for nextValidId callback).")
        valid_order_id = int(self.next_order_id)
        self.next_order_id += 1
        return valid_order_id

    def _ensure_ohlc_df(self, local_symbol: str, timeframe: str) -> pd.DataFrame:
        """Ensure DataFrame exists for symbol/timeframe and return it."""
        if local_symbol not in self.ohlc_data:
            self.ohlc_data[local_symbol] = {}
        if timeframe not in self.ohlc_data[local_symbol]:
            self.ohlc_data[local_symbol][timeframe] = {
                "data": pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
            }
        return self.ohlc_data[local_symbol][timeframe]["data"]

    @staticmethod
    def _parse_bar_datetime(date_field: Any) -> tuple[int, datetime]:
        """
        Parse IBKR BarData.date into (epoch_seconds, datetime).

        IBKR can send:
        - epoch seconds as a string (intraday)
        - 'YYYYMMDD' (daily bars with formatDate=1)
        - 'YYYYMMDD HH:MM:SS' (intraday bars with formatDate=1)
        """
        raw = str(date_field).strip()
        normalized = " ".join(raw.split())

        if normalized.isdigit():
            # Daily bars often come as YYYYMMDD; intraday can be epoch seconds.
            if len(normalized) == 8:
                dt = datetime.strptime(normalized, "%Y%m%d")
                ts = int(dt.timestamp())
                return ts, dt

            ts = int(normalized)
            dt = datetime.fromtimestamp(ts)
            return ts, dt

        dt = datetime.strptime(normalized, "%Y%m%d %H:%M:%S")
        ts = int(dt.timestamp())
        return ts, dt

    # ---- EWrapper callbacks ----
    def nextValidId(self, orderId: int) -> None:
        self.next_order_id = int(orderId)

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str) -> None:
        if currency == "BASE":
            if key == "CashBalance":
                # Cash recognized at the time of trade + futures PNL
                self.account_balance = round(float(val), 2)
            elif key == "NetLiquidationByCurrency":
                # Net liquidation for individual currencies
                self.account_equity = round(float(val), 2)

        if key == "MaintMarginReq":
            self.maintenance_margin = round(float(val), 2)
        elif key == "ExcessLiquidity":
            self.free_margin = round(float(val), 2)

    def updatePortfolio(
        self,
        contract: Contract,
        position: float,
        marketPrice: float,
        marketValue: float,
        averageCost: float,
        unrealizedPNL: float,
        realizedPNL: float,
        accountName: str,
    ) -> None:
        self.portfolio[contract.localSymbol] = {
            "position": position,
            "marketPrice": marketPrice,
            "marketValue": marketValue,
            "averageCost": averageCost,
            "unrealizedPNL": unrealizedPNL,
            "realizedPNL": realizedPNL,
        }

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib) -> None:
        local_symbol = self.req_mkt_map[reqId]
        if tickType in (1, 66):
            self.marketdata[local_symbol]["bid"] = price
        elif tickType in (2, 67):
            self.marketdata[local_symbol]["ask"] = price
        elif tickType in (4, 68):
            self.marketdata[local_symbol]["last"] = price

    def tickSize(self, reqId: TickerId, tickType: TickType, size: Decimal) -> None:
        local_symbol = self.req_mkt_map[reqId]

        if tickType == 0:
            self.marketdata[local_symbol]["bid_size"] = decimalMaxString(size)
            self.marketdata[local_symbol]["bid_time"] = datetime.now()
        elif tickType == 3:
            self.marketdata[local_symbol]["ask_size"] = decimalMaxString(size)
            self.marketdata[local_symbol]["ask_time"] = datetime.now()
        elif tickType == 5:
            self.marketdata[local_symbol]["last_size"] = decimalMaxString(size)
            self.marketdata[local_symbol]["last_time"] = datetime.now()

    def historicalData(self, reqId: int, bar: BarData) -> None:
        local_symbol = self.req_hist_map[reqId]["local_symbol"]
        timeframe = self.req_hist_map[reqId]["timeframe"]

        time, time_dt = self._parse_bar_datetime(bar.date)
        df = self._ensure_ohlc_df(local_symbol, timeframe)
        df.loc[time, ["time", "open", "high", "low", "close", "volume"]] = [
            time_dt,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            decimalMaxString(bar.volume),
        ]

    def historicalDataUpdate(self, reqId: int, bar: BarData) -> None:
        local_symbol = self.req_hist_map[reqId]["local_symbol"]
        timeframe = self.req_hist_map[reqId]["timeframe"]

        time, time_dt = self._parse_bar_datetime(bar.date)
        df = self._ensure_ohlc_df(local_symbol, timeframe)
        df.loc[time, ["time", "open", "high", "low", "close", "volume"]] = [
            time_dt,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            decimalMaxString(bar.volume),
        ]

    def historicalDataEnd(self, reqId: int, start: str, end: str) -> None:
        local_symbol = self.req_hist_map[reqId]["local_symbol"]
        timeframe = self.req_hist_map[reqId]["timeframe"]

        self._ensure_ohlc_df(local_symbol, timeframe)
        self.ohlc_data[local_symbol][timeframe]["end"] = datetime.now()
        self.ohlc_data[local_symbol][timeframe]["start_str"] = start
        self.ohlc_data[local_symbol][timeframe]["end_str"] = end

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState) -> None:
        self.orders[int(orderId)] = {
            "local_symbol": contract.localSymbol,
            "commission": orderState.commission,
            "commission_currency": orderState.commissionCurrency,
            "completed_status": orderState.completedStatus,
            "start_time": order.activeStartTime,
            "action": order.action,
            "order_type": order.orderType,
            "quantity": decimalMaxString(order.totalQuantity),
            "tif": order.tif,
            "lmt_price": order.lmtPrice,
            "aux_price": order.auxPrice,
        }

    def orderStatus(
        self,
        orderId: OrderId,
        status: str,
        filled: Decimal,
        remaining: Decimal,
        avgFillPrice: float,
        permId: int,
        parentId: int,
        lastFillPrice: float,
        clientId: int,
        whyHeld: str,
        mktCapPrice: float,
    ) -> None:
        super().orderStatus(
            orderId,
            status,
            filled,
            remaining,
            avgFillPrice,
            permId,
            parentId,
            lastFillPrice,
            clientId,
            whyHeld,
            mktCapPrice,
        )
        oid = int(orderId)
        if oid in self.orders:
            self.orders[oid]["status"] = status
            if status == "Filled":
                self.orders[oid]["has_been_filled"] = True

    def execDetails(self, reqId: int, contract: Contract, execution: Execution) -> None:
        self.executions[execution.execId] = {
            "symbol": contract.localSymbol,
            "time": execution.time,
            "account": execution.acctNumber,
            "action": execution.side,
            "quantity": float(decimalMaxString(execution.shares)),
            "price": execution.price,
        }

    def commissionReport(self, commissionReport: CommissionReport) -> None:
        # IB sends 1.7976931348623157e+308 (max float) when no realized PNL
        realized_pnl = 0.0 if commissionReport.realizedPNL == 1.7976931348623157e+308 else float(commissionReport.realizedPNL)
        self.commission_report[commissionReport.execId] = {
            "commission": commissionReport.commission,
            "commission_currency": commissionReport.currency,
            "realized_pnl": realized_pnl,
        }


class TWS_Wrapper_Client:
    """Thin wrapper around ibapi EClient/EWrapper with convenience helpers."""

    def __init__(self, host: str, port: int, client_id: int, ib_account: str) -> None:
        self.trade_app = TradeApp()

        self.trade_app.connect(host, int(port), int(client_id))
        sleep(1)

        self.app_thread = Thread(target=self.trade_app.run, daemon=True)
        self.app_thread.start()

        # requesting Account Updates
        self.trade_app.reqAccountUpdates(subscribe=True, acctCode=ib_account)

        # requesting Open Orders
        self.trade_app.reqAllOpenOrders()

        # Assigning manually opened orders to API
        self.trade_app.reqAutoOpenOrders(True)

        # Requesting Executions for the day
        self.trade_app.reqExecutions(reqId=1, execFilter=ExecutionFilter())

    def get_contract(self, symbol: str, contract_id: int, exchange: str) -> Contract:
        contract = Contract()
        contract.localSymbol = symbol
        contract.conId = int(contract_id)
        contract.exchange = exchange
        return contract

    def request_market_data(self, contract: Contract, *, delayed: bool = False, req_id: int | None = None) -> None:
        """Request live/delayed market data for a contract."""
        if delayed:
            # 1=live, 2=frozen, 3=delayed, 4=delayed frozen
            self.trade_app.reqMarketDataType(3)

        if req_id is None:
            req_id = self.trade_app.req_mkt_id
            self.trade_app.req_mkt_id += 1

        symbol = getattr(contract, "localSymbol", None) or getattr(contract, "symbol", None) or str(req_id)
        self.trade_app.req_mkt_map[int(req_id)] = str(symbol)
        self.trade_app.marketdata.setdefault(str(symbol), {})

        self.trade_app.reqMktData(int(req_id), contract, "", False, False, [])

    def request_historical_data(
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
        """Request historical data for a contract."""
        if req_id is None:
            req_id = self.trade_app.req_hist_data_id
            self.trade_app.req_hist_data_id += 1

        local_symbol = getattr(contract, "localSymbol", None) or getattr(contract, "symbol", None) or str(req_id)
        self.trade_app.req_hist_map[int(req_id)] = {
            "local_symbol": str(local_symbol),
            "timeframe": str(bar_size),
        }
        self.trade_app.ohlc_data.setdefault(str(local_symbol), {})

        self.trade_app.reqHistoricalData(
            reqId=int(req_id),
            contract=contract,
            endDateTime="",
            durationStr=str(duration),
            barSizeSetting=str(bar_size),
            whatToShow=str(what_to_show),
            useRTH=int(use_rth),
            formatDate=1,
            keepUpToDate=bool(keep_up_to_date),
            chartOptions=[],
        )

    def get_account_data(self) -> dict[str, float | None]:
        return {
            "account_balance": self.trade_app.account_balance,
            "account_equity": self.trade_app.account_equity,
            "maintenance_margin": self.trade_app.maintenance_margin,
            "free_margin": self.trade_app.free_margin,
        }

    def get_positions(self) -> dict[str, dict[str, Any]]:
        return self.trade_app.portfolio

    def get_orders(self) -> dict[int, dict[str, Any]]:
        return self.trade_app.orders

    def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
        return self.trade_app.orders.get(int(order_id))

    def get_market_data_price(self, symbol: str) -> dict[str, Any]:
        """Return full marketdata dict for a symbol (bid/ask/last + sizes/times)."""
        return self.trade_app.marketdata.get(symbol, {})

    def get_trade_report(self) -> list[dict[str, Any]]:
        executions = self.trade_app.executions
        commissions = self.trade_app.commission_report

        trade_report: list[dict[str, Any]] = []
        for k, v in executions.copy().items():
            comm = commissions.get(k, {})
            v = dict(v)
            v["commission"] = comm.get("commission")
            v["commission_currency"] = comm.get("commission_currency")
            trade_report.append(v)

        return trade_report

    def get_exposure_by_symbol(self, symbol: str) -> int:
        """Return the current open volume on a symbol."""
        try:
            exposure = self.trade_app.portfolio[symbol]["position"]
        except KeyError:
            exposure = 0
        return int(exposure)

    def get_ohlc_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        return self.trade_app.ohlc_data[symbol][timeframe]["data"]

    def wait_for_historical_data(
        self, symbol: str, timeframe: str, *, timeout_s: float = 30.0, poll_s: float = 0.1
    ) -> bool:
        """Wait until initial historical batch has completed for symbol/timeframe."""
        deadline = datetime.now() + timedelta(seconds=float(timeout_s))
        while datetime.now() < deadline:
            tf_data = self.trade_app.ohlc_data.get(symbol, {}).get(timeframe)
            if tf_data and tf_data.get("end") and hasattr(tf_data.get("data"), "empty") and not tf_data["data"].empty:
                return True
            sleep(float(poll_s))
        return False

    def send_market_order(self, contract: Contract, action: str, quantity: int, tif: str = "DAY") -> dict[str, int]:
        market_order = Order()
        market_order.action = str(action)
        market_order.orderType = "MKT"
        market_order.totalQuantity = int(quantity)
        market_order.tif = str(tif)

        next_valid_id = self.trade_app._get_next_valid_id()
        self.trade_app.placeOrder(int(next_valid_id), contract, market_order)
        return {"order_id": int(next_valid_id)}

    def send_limit_order(
        self,
        contract: Contract,
        action: str,
        quantity: int,
        limit_price: float,
        tif: str = "DAY",
        all_or_none: bool = True,
    ) -> dict[str, int]:
        limit_order = Order()
        limit_order.action = str(action)
        limit_order.orderType = "LMT"
        limit_order.lmtPrice = float(limit_price)
        limit_order.totalQuantity = int(quantity)
        limit_order.tif = str(tif)
        limit_order.allOrNone = bool(all_or_none)

        next_valid_id = self.trade_app._get_next_valid_id()
        self.trade_app.placeOrder(int(next_valid_id), contract, limit_order)

        timeout_until = datetime.now() + timedelta(seconds=15)
        while datetime.now() < timeout_until:
            if self.trade_app.orders.get(int(next_valid_id)):
                return {"order_id": int(next_valid_id)}
            sleep(0.1)
        return {"order_id": int(next_valid_id)}

    def send_stop_order(
        self,
        contract: Contract,
        action: str,
        quantity: int,
        stop_price: float,
        tif: str = "DAY",
        all_or_none: bool = True,
    ) -> dict[str, int]:
        stop_order = Order()
        stop_order.action = str(action)
        stop_order.orderType = "STP"
        stop_order.auxPrice = float(stop_price)
        stop_order.totalQuantity = int(quantity)
        stop_order.tif = str(tif)
        stop_order.allOrNone = bool(all_or_none)

        next_valid_id = self.trade_app._get_next_valid_id()
        self.trade_app.placeOrder(int(next_valid_id), contract, stop_order)

        timeout_until = datetime.now() + timedelta(seconds=15)
        while datetime.now() < timeout_until:
            if self.trade_app.orders.get(int(next_valid_id)):
                return {"order_id": int(next_valid_id)}
            sleep(0.1)
        return {"order_id": int(next_valid_id)}

    def cancel_order(self, order_id: int) -> dict[str, int]:
        self.trade_app.cancelOrder(int(order_id))
        return {"order_id": int(order_id)}

    def disconnect(self) -> None:
        """Disconnect from TWS/IB Gateway."""
        if self.trade_app.isConnected():
            self.trade_app.disconnect()

