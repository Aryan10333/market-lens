"""Splits, bonuses and consolidations: reading NSE's wording and using the result.

Stored prices are raw (as published by NSE). NSE does **not** adjust old prices, and does
not adjust `prev_close` on the ex-date either: on RELIANCE's 1:1 bonus ex-date the share
opened at 1337 while prev_close still said 2655.70.

So the official action list is the source of truth. Each action gives a factor:
every price BEFORE the ex-date is multiplied by it, which makes old and new prices comparable.

  Bonus 1:1                 -> 0.5    (1 free share for every 1 held: twice as many shares)
  Bonus 1:2                 -> 0.6667 (1 free share for every 2 held)
  Split from Rs 10 to Re 1  -> 0.1
  Consolidation Re 1 to 10  -> 10     (reverse split: fewer, pricier shares)

Dividends, rights issues, buybacks and demergers are ignored: they do not multiply the
share count, and NSE does not adjust prices for them either.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# "Bonus 1:1", but not "Bonus Ncrps 1:10" (preference shares: equity share count is unchanged)
BONUS = re.compile(r"^bonus\s+(\d+)\s*:\s*(\d+)$")
# "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share"
SPLIT = re.compile(
    r"split.*?from\s*(?:rs|re)\.?\s*([\d.]+).*?to\s*(?:rs|re)\.?\s*([\d.]+)",
)
# "Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share"
CONSOLIDATION = re.compile(
    r"consolidation.*?from\s*(?:rs|re)\.?\s*([\d.]+).*?to\s*(?:rs|re)\.?\s*([\d.]+)",
)


@dataclass(frozen=True)
class Action:
    kind: str  # 'bonus', 'split' or 'consolidation'
    factor: Decimal


def parse_action(subject: str) -> Action | None:
    """Turn NSE's description into a price factor. Returns None for anything else."""
    text = " ".join(subject.lower().split())

    m = BONUS.match(text)
    if m:
        new, held = Decimal(m.group(1)), Decimal(m.group(2))
        # `held` shares become `held + new` shares
        return Action("bonus", _round(held / (held + new)))

    for kind, pattern in (("split", SPLIT), ("consolidation", CONSOLIDATION)):
        m = pattern.search(text)
        if m:
            before, after = Decimal(m.group(1)), Decimal(m.group(2))
            if before > 0 and after > 0:
                return Action(kind, _round(after / before))
    return None


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"))


def adjustment_multiplier(day: date, factors: list[tuple[date, Decimal]]) -> Decimal:
    """Number to multiply a raw price on `day` by, to compare it with today's prices.

    factors: (ex_date, factor) pairs for one company.
    """
    m = Decimal(1)
    for ex_date, factor in factors:
        if day < ex_date:
            m *= factor
    return m
