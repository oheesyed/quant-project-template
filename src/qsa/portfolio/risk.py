from __future__ import annotations


def clamp_target_position(target: float, max_abs_position: float) -> float:
    if target > max_abs_position:
        return max_abs_position
    if target < -max_abs_position:
        return -max_abs_position
    return target

