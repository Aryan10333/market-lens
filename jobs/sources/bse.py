"""BSE files. For now only used to find each company's BSE scrip code from its ISIN."""

import csv
import io
from datetime import date

REFERER = "https://www.bseindia.com/"


def bhavcopy_url(day: date) -> str:
    return (
        "https://www.bseindia.com/download/BhavCopy/Equity/"
        f"BhavCopy_BSE_CM_0_0_0_{day:%Y%m%d}_F_0000.CSV"
    )


def parse_scrip_codes(csv_text: str) -> dict[str, str]:
    """Return {ISIN: BSE scrip code} for company shares (ISIN starting with INE).

    Returns an empty dict if the text is not a BSE bhavcopy (BSE sometimes sends an HTML page).
    """
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("﻿")))
    if not reader.fieldnames or "FinInstrmId" not in reader.fieldnames:
        return {}
    codes = {}
    for r in reader:
        isin = (r.get("ISIN") or "").strip().upper()
        code = (r.get("FinInstrmId") or "").strip()
        if (
            isin.startswith("INE")
            and code.isdigit()
            and (r.get("FinInstrmTp") or "").strip() == "STK"
        ):
            codes[isin] = code
    return codes
