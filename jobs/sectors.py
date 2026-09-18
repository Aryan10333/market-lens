"""Which NSE index represents each sector.

`companies.sector` uses NSE's own sector labels (from the Nifty 500 list). To judge whether a
sector is doing well, each label is matched to the NSE sector index that tracks it.

Two labels have no sector index and are left out: "Textiles" and "Diversified".
Their companies still appear in every other scanner.
"""

SECTOR_INDEX = {
    "Automobile and Auto Components": "Nifty Auto",
    "Capital Goods": "Nifty Capital Goods",
    "Chemicals": "Nifty Chemicals",
    "Construction": "Nifty Construction",
    "Construction Materials": "Nifty Cement",
    "Consumer Durables": "Nifty Consumer Durables",
    "Consumer Services": "Nifty Consumer Services",
    "Fast Moving Consumer Goods": "Nifty FMCG",
    "Financial Services": "Nifty Financial Services",
    "Healthcare": "Nifty Healthcare Index",
    "Information Technology": "Nifty IT",
    "Media Entertainment & Publication": "Nifty Media",
    "Metals & Mining": "Nifty Metal",
    "Oil Gas & Consumable Fuels": "Nifty Oil & Gas",
    "Power": "Nifty Power",
    "Realty": "Nifty Realty",
    "Services": "Nifty Services Sector",
    "Telecommunication": "Nifty Telecommunications",
}

SECTORS_WITHOUT_INDEX = ["Textiles", "Diversified"]
