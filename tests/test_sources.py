from datetime import date
from decimal import Decimal

from jobs.sources import bse, nse

UDIFF = """TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4
2026-09-16,2026-09-16,CM,NSE,STK,2885,INE002A01018,RELIANCE,EQ,,,,,RELIANCE INDUSTRIES LTD,1400.00,1420.50,1395.10,1410.25,1411.00,1398.00,,1410.25,,,5000000,7051250000.00,120000,F1,1,,,,,
2026-09-16,2026-09-16,CM,NSE,STK,19078,IN0020200104,SGBJUN28,GB,,,,,2.5%GOLDBONDS2028SR-II,9000,9000,9000,9000,9000,9000,,9000,,,10,90000,1,F1,1,,,,,
2026-09-16,2026-09-16,CM,NSE,STK,1,INF204KB14I2,NIFTYBEES,EQ,,,,,NIPPON ETF,280,281,279,280.5,280.5,279,,280.5,,,100,28050,5,F1,1,,,,,
2026-09-16,2026-09-16,CM,NSE,STK,2,INE123A01011,SMALLCO,BE,,,,,SMALL CO LTD,50.00,52.00,49.00,51.00,51.00,,,51,,,1000,51000.00,,F1,1,,,,,
"""

LEGACY = """SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,
RELIANCE,EQ,2400,2420,2390,2410.5,2411,2398,4000000,9642000000,15-SEP-2023,100000,INE002A01018,
1018GS2026,GS,130,130,130,130,130,130,51,6630,15-SEP-2023,2,IN0020010081,
"""

INDEX_CLOSE = """Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield
Nifty 500,16-09-2026,21000.5,21100,20950.25,21080.75,80,.38,500000000,40000,22.1,3.9,1.1
India VIX,16-09-2026,-,-,-,12.34,-0.2,-1.6,-,-,-,-,-
Broken Row,16-09-2026,1,1,1,-,0,0,0,0,0,0,0
"""

NIFTY500 = """Company Name,Industry,Symbol,Series,ISIN Code
360 ONE WAM Ltd.,Financial Services,360ONE,EQ,INE466L01038
3M India Ltd.,Diversified,3MINDIA,EQ,INE470A01017
Bad Row,Diversified,,EQ,
"""

BSE_BHAV = """TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4
2026-09-16,2026-09-16,CM,BSE,STK,500325,INE002A01018,RELIANCE,A,,,,,RELIANCE INDUSTRIES LTD.,1400,1420,1395,1410,1410,1398,,1410,,,100,141000,10,F1,1,,,,,
2026-09-16,2026-09-16,CM,BSE,STK,800001,INF204KB14I2,NIFTYBEES,E,,,,,NIPPON ETF,280,281,279,280,280,279,,280,,,1,280,1,F1,1,,,,,
"""


def test_udiff_keeps_only_company_equity_rows():
    rows, total = nse.parse_bhavcopy(UDIFF, "udiff")
    assert total == 4
    assert [r.symbol for r in rows] == ["RELIANCE", "SMALLCO"]  # no gold bond, no ETF
    rel = rows[0]
    assert rel.trade_date == date(2026, 9, 16)
    assert rel.close == Decimal("1410.25")
    assert rel.prev_close == Decimal("1398.00")
    assert rel.volume == 5_000_000
    assert rel.num_trades == 120_000


def test_udiff_handles_blank_optional_fields():
    rows, _ = nse.parse_bhavcopy(UDIFF, "udiff")
    small = rows[1]
    assert small.series == "BE"
    assert small.prev_close is None
    assert small.num_trades is None


def test_legacy_format():
    rows, total = nse.parse_bhavcopy(LEGACY, "legacy")
    assert total == 2
    assert len(rows) == 1
    assert rows[0].trade_date == date(2023, 9, 15)
    assert rows[0].close == Decimal("2410.5")


def test_validate_price_catches_bad_rows():
    rows, _ = nse.parse_bhavcopy(UDIFF, "udiff")
    good = rows[0]
    assert nse.validate_price(good) == []
    bad = nse.PriceRow(**{**good.__dict__, "close": Decimal("1500")})
    assert "close outside low-high range" in nse.validate_price(bad)
    bad = nse.PriceRow(**{**good.__dict__, "low": Decimal("1500")})
    assert "low above high" in nse.validate_price(bad)


def test_index_close_parsing():
    rows = nse.parse_index_close(INDEX_CLOSE)
    assert [r.index_name for r in rows] == ["Nifty 500", "India VIX"]  # broken row skipped
    assert rows[0].close == Decimal("21080.75")
    assert rows[1].open is None  # '-' becomes empty
    assert rows[0].trade_date == date(2026, 9, 16)


def test_nifty500_list_parsing():
    rows = nse.parse_nifty500_list(NIFTY500)
    assert len(rows) == 2
    assert rows[0].symbol == "360ONE"
    assert rows[0].industry == "Financial Services"
    assert rows[0].isin == "INE466L01038"


def test_bhavcopy_urls_try_udiff_then_legacy():
    urls = nse.bhavcopy_urls(date(2024, 7, 5))
    assert urls[0] == (
        "udiff",
        "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20240705_F_0000.csv.zip",
    )
    assert urls[1][1].endswith("/2024/JUL/cm05JUL2024bhav.csv.zip")


def test_bse_scrip_codes_only_company_shares():
    assert bse.parse_scrip_codes(BSE_BHAV) == {"INE002A01018": "500325"}


def test_bse_html_page_gives_no_codes():
    assert bse.parse_scrip_codes("<!DOCTYPE html><html>error</html>") == {}
