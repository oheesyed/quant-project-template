"""Trading strategies (pure decision logic).

Convention for strategy modules:
- export `Params` (a dataclass for strategy inputs)
- export `decide_target_position(ohlc, position, p)` returning target shares
"""

