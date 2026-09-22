"""State machine for strategy variants A, B, C.

Variant A: opposite-band exit/reversal; hold through noise area.
Variant B/C: exit when price crosses current-band+VWAP stop; operational entry
requires price beyond max(U,VWAP) / min(L,VWAP).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Literal


class Position(IntEnum):
    FLAT = 0
    LONG = 1
    SHORT = -1


Variant = Literal["A", "B", "C"]


@dataclass
class Decision:
    target: Position
    reason: str


def decide_A(pos: Position, price: float, upper: float, lower: float) -> Decision:
    """Opposite-band stop / reverse. Returning inside bands alone does not flatten."""
    if not (price == price and upper == upper and lower == lower):  # NaN check
        return Decision(Position.FLAT if pos == Position.FLAT else pos, "nan_bands_hold_or_flat")

    if pos == Position.FLAT:
        if price > upper:
            return Decision(Position.LONG, "A_enter_long")
        if price < lower:
            return Decision(Position.SHORT, "A_enter_short")
        return Decision(Position.FLAT, "A_stay_flat")

    if pos == Position.LONG:
        if price < lower:
            return Decision(Position.SHORT, "A_reverse_to_short")
        return Decision(Position.LONG, "A_hold_long")

    # SHORT
    if price > upper:
        return Decision(Position.LONG, "A_reverse_to_long")
    return Decision(Position.SHORT, "A_hold_short")


def decide_BC(
    pos: Position,
    price: float,
    upper: float,
    lower: float,
    vwap: float,
    use_vwap: bool = True,
) -> Decision:
    """Current-band (+ optional VWAP) stops.

    Operational entry convention (documented adaptation of combined conditions):
      long eligibility:  price > max(U, VWAP)  [or > U if not use_vwap]
      short eligibility: price < min(L, VWAP)  [or < L if not use_vwap]
    Exit long when price < long_stop; exit short when price > short_stop.
    Strict inequalities for entries; stops use strict < / > as well.
    Exact equality: remain in current state (no entry / no stop trigger).
    """
    if not (price == price and upper == upper and lower == lower):
        return Decision(Position.FLAT if pos == Position.FLAT else pos, "nan_bands_hold_or_flat")
    if use_vwap and not (vwap == vwap):
        # If VWAP missing, fall back to band-only for this bar
        use_vwap = False

    if use_vwap:
        long_stop = max(upper, vwap)
        short_stop = min(lower, vwap)
        long_entry = long_stop
        short_entry = short_stop
    else:
        long_stop = upper
        short_stop = lower
        long_entry = upper
        short_entry = lower

    if pos == Position.FLAT:
        if price > long_entry:
            return Decision(Position.LONG, "BC_enter_long")
        if price < short_entry:
            return Decision(Position.SHORT, "BC_enter_short")
        return Decision(Position.FLAT, "BC_stay_flat")

    if pos == Position.LONG:
        if price < long_stop:
            # Check reverse eligibility in same bar after exit
            if price < short_entry:
                return Decision(Position.SHORT, "BC_exit_long_reverse_short")
            return Decision(Position.FLAT, "BC_exit_long")
        return Decision(Position.LONG, "BC_hold_long")

    # SHORT
    if price > short_stop:
        if price > long_entry:
            return Decision(Position.LONG, "BC_exit_short_reverse_long")
        return Decision(Position.FLAT, "BC_exit_short")
    return Decision(Position.SHORT, "BC_hold_short")


def decide(
    variant: Variant,
    pos: Position,
    price: float,
    upper: float,
    lower: float,
    vwap: float,
    use_vwap: bool = True,
) -> Decision:
    if variant == "A":
        return decide_A(pos, price, upper, lower)
    return decide_BC(pos, price, upper, lower, vwap, use_vwap=use_vwap)
