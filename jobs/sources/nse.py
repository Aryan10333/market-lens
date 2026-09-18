"""NSE files: equity bhavcopy (daily prices), index closing values, Nifty 500 list.

Two bhavcopy formats exist:
  * "udiff"  : BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip  (from January 2024)
  * "legacy" : cmDDMONYYYYbhav.csv.zip                        (older days, until July 2024)
Downloads try udiff first, then legacy.
"""

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

REFERER = "https://www.nseindia.com/"

# Series that are normal equity shares. EQ = rolling settlement, BE/BZ = trade-for-trade.
EQUITY_SERIES = {"EQ", "BE", "BZ"}

NIFTY500_LIST_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"

# The corporate actions list (bonuses, splits, dividends...) is a JSON API on the main site.
CORPORATE_ACTIONS_REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-actions"


@dataclass(frozen=True)
class PriceRow:
    trade_date: date
    symbol: str
    series: str
    isin: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    prev_close: Decimal | None
    volume: int
    traded_value: Decimal
    num_trades: int | None


@dataclass(frozen=True)
class IndexRow:
    index_name: str
    trade_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal


@dataclass(frozen=True)
class CorporateActionRow:
    isin: str
    symbol: str
    ex_date: date
    subject: str


@dataclass(frozen=True)
class UniverseRow:
    name: str
    industry: str
    symbol: str
    series: str
    isin: str


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
def bhavcopy_urls(day: date) -> list[tuple[str, str]]:
    """(format, url) pairs to try, in order."""
    mon = day.strftime("%b").upper()
    return [
        (
            "udiff",
            "https://nsearchives.nseindia.com/content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip",
        ),
        (
            "legacy",
            "https://nsearchives.nseindia.com/content/historical/EQUITIES/"
            f"{day:%Y}/{mon}/cm{day:%d}{mon}{day:%Y}bhav.csv.zip",
        ),
    ]


def corporate_actions_url(start: date, end: date) -> str:
    return (
        "https://www.nseindia.com/api/corporates-corporateActions?index=equities"
        f"&from_date={start:%d-%m-%Y}&to_date={end:%d-%m-%Y}"
    )


def index_close_url(day: date) -> str:
    return f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{day:%d%m%Y}.csv"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _dec(value: str | None) -> Decimal | None:
    """Text to Decimal. Empty, '-' or invalid -> None."""
    if value is None:
        return None
    value = value.strip()
    if value in ("", "-"):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _int(value: str | None) -> int | None:
    d = _dec(value)
    return int(d) if d is not None else None


def _rows(text: str) -> list[dict[str, str]]:
    """CSV text to a list of dicts, with header names and values trimmed."""
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    header = [h.strip() for h in next(reader, [])]
    return [
        {h: (v.strip() if v else "") for h, v in zip(header, values, strict=False)}
        for values in reader
        if values
    ]


# ---------------------------------------------------------------------------
# Bhavcopy
# ---------------------------------------------------------------------------
def parse_bhavcopy(csv_text: str, file_format: str) -> tuple[list[PriceRow], int]:
    """Parse a bhavcopy CSV. Returns (equity rows, total rows in file).

    Only equity series (EQ/BE/BZ) with an Indian company ISIN (INE...) are returned.
    Rows missing a required number are skipped.
    """
    if file_format == "udiff":
        cols = dict(
            date="TradDt", symbol="TckrSymb", series="SctySrs", isin="ISIN", open="OpnPric",
            high="HghPric", low="LwPric", close="ClsPric", prev="PrvsClsgPric",
            volume="TtlTradgVol", value="TtlTrfVal", trades="TtlNbOfTxsExctd",
        )  # fmt: skip
        date_fmt = "%Y-%m-%d"
    elif file_format == "legacy":
        cols = dict(
            date="TIMESTAMP", symbol="SYMBOL", series="SERIES", isin="ISIN", open="OPEN",
            high="HIGH", low="LOW", close="CLOSE", prev="PREVCLOSE",
            volume="TOTTRDQTY", value="TOTTRDVAL", trades="TOTALTRADES",
        )  # fmt: skip
        date_fmt = "%d-%b-%Y"
    else:
        raise ValueError(f"Unknown bhavcopy format: {file_format}")

    raw = _rows(csv_text)
    out = []
    for r in raw:
        series = r.get(cols["series"], "").upper()
        isin = r.get(cols["isin"], "").upper()
        if series not in EQUITY_SERIES or not isin.startswith("INE"):
            continue
        o, h, lo, c = (_dec(r.get(cols[k])) for k in ("open", "high", "low", "close"))
        volume, value = _int(r.get(cols["volume"])), _dec(r.get(cols["value"]))
        if None in (o, h, lo, c, volume, value):
            continue
        out.append(
            PriceRow(
                trade_date=datetime.strptime(r[cols["date"]], date_fmt).date(),
                symbol=r[cols["symbol"]].upper(),
                series=series,
                isin=isin,
                open=o,
                high=h,
                low=lo,
                close=c,
                prev_close=_dec(r.get(cols["prev"])),
                volume=volume,
                traded_value=value,
                num_trades=_int(r.get(cols["trades"])),
            )
        )
    return out, len(raw)


def validate_price(row: PriceRow) -> list[str]:
    """Return a list of problems with a price row. Empty list = row is fine."""
    problems = []
    if min(row.open, row.high, row.low, row.close) <= 0:
        problems.append("price not positive")
    if row.low > row.high:
        problems.append("low above high")
    if not (row.low <= row.close <= row.high):
        problems.append("close outside low-high range")
    if not (row.low <= row.open <= row.high):
        problems.append("open outside low-high range")
    if row.volume < 0 or row.traded_value < 0:
        problems.append("negative volume or value")
    return problems


# ---------------------------------------------------------------------------
# Index closing values
# ---------------------------------------------------------------------------
def parse_index_close(csv_text: str) -> list[IndexRow]:
    out = []
    for r in _rows(csv_text):
        name = r.get("Index Name", "")
        close = _dec(r.get("Closing Index Value"))
        date_text = r.get("Index Date", "")
        if not name or close is None or not date_text:
            continue
        out.append(
            IndexRow(
                index_name=name,
                trade_date=datetime.strptime(date_text, "%d-%m-%Y").date(),
                open=_dec(r.get("Open Index Value")),
                high=_dec(r.get("High Index Value")),
                low=_dec(r.get("Low Index Value")),
                close=close,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Corporate actions
# ---------------------------------------------------------------------------
def parse_corporate_actions(json_text: str) -> list[CorporateActionRow]:
    """Read the corporate actions JSON. Rows without a usable ex-date are skipped."""
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    out = []
    for r in data:
        isin = (r.get("isin") or "").strip().upper()
        ex_text = (r.get("exDate") or "").strip()
        subject = (r.get("subject") or "").strip()
        if not isin.startswith("INE") or not subject or ex_text in ("", "-"):
            continue
        try:
            ex_date = datetime.strptime(ex_text, "%d-%b-%Y").date()
        except ValueError:
            continue
        out.append(
            CorporateActionRow(
                isin=isin,
                symbol=(r.get("symbol") or "").strip().upper(),
                ex_date=ex_date,
                subject=subject,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Nifty 500 constituents
# ---------------------------------------------------------------------------
def parse_nifty500_list(csv_text: str) -> list[UniverseRow]:
    out = []
    for r in _rows(csv_text):
        isin = r.get("ISIN Code", "").upper()
        symbol = r.get("Symbol", "").upper()
        if not isin.startswith("IN") or not symbol:
            continue
        out.append(
            UniverseRow(
                name=r.get("Company Name", ""),
                industry=r.get("Industry", ""),
                symbol=symbol,
                series=r.get("Series", ""),
                isin=isin,
            )
        )
    return out
