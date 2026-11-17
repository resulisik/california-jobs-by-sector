"""Paths and series definitions shared by every script."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_BLS = ROOT / "data" / "raw" / "bls"
RAW_INDEED = ROOT / "data" / "raw" / "indeed"
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "sectors.db"
SQL_DIR = ROOT / "sql"
CHARTS = ROOT / "charts"
DOCS = ROOT / "docs"
RAW_STOCKS = ROOT / "data" / "raw" / "stocks"
RESEARCH = ROOT / "data" / "research"

# Analysis window: 5 years ending in the latest month BLS has published.
START_MONTH = "2021-09-01"
END_MONTH = "2026-09-01"
PRE_PANDEMIC = "2020-02-01"
# Stocks and national jobs are published a month ahead of state data.
STOCK_START = "2021-10-01"
STOCK_END = "2026-10-01"

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2020-01-01"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1mo&events=div"
INDEED_RAW = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/{path}"
INDEED_FILES = {
    "state_job_postings_us.csv": "US/state_job_postings_us.csv",
    "metro_job_postings_us.csv": "US/metro_job_postings_us.csv",
    "job_postings_by_sector_US.csv": "US/job_postings_by_sector_US.csv",
    "aggregate_job_postings_US.csv": "US/aggregate_job_postings_US.csv",
}

# BLS Current Employment Statistics series for California (thousands of jobs).
# level: total / supersector / subsector / area.  sa: seasonally adjusted?
SERIES = [
    # id,                    name,                                   level,         sa,    file,                     region
    ("CANA",                 "Total nonfarm",                        "total",       True,  "ca_supersectors_sa.csv", "CA"),
    ("CAEDUH",               "Private education & health services",  "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CALEIH",               "Leisure & hospitality",                "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CATRAD",               "Trade, transportation & utilities",    "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CAGOVT",               "Government",                           "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CASRVO",               "Other services",                       "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CANRMN",               "Mining & logging",                     "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CACONS",               "Construction",                         "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CAPBSV",               "Professional & business services",     "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CAMFG",                "Manufacturing",                        "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("CAFIRE",               "Financial activities",                 "supersector", True,  "ca_supersectors_sa.csv", "CA"),
    ("SMS06000005000000001", "Information",                          "supersector", True,  "ca_subsectors.csv", "CA"),
    ("SMS06000006562000001", "Health care & social assistance",      "subsector",   True,  "ca_subsectors.csv", "CA"),
    ("SMS06000006054000001", "Professional, scientific & technical", "subsector",   True,  "ca_subsectors.csv", "CA"),
    ("SMS06000004300000001", "Transportation, warehousing & utilities", "subsector",   True,  "ca_subsectors.csv", "CA"),
    ("SMS06000004200000001", "Retail trade",                         "subsector",   True,  "ca_subsectors.csv", "CA"),
    ("SMS06000007072000001", "Accommodation & food services",        "subsector",   True,  "ca_subsectors.csv", "CA"),
    ("SMU06000003133640001", "Aerospace product & parts",            "subsector",   False, "ca_subsectors.csv", "CA"),
    ("SMU06000005051200001", "Motion picture & sound recording",     "subsector",   False, "ca_subsectors.csv", "CA"),
    ("SMU06000006054150001", "Computer systems design",              "subsector",   False, "ca_subsectors.csv", "CA"),
    ("SMU06310840000000001", "Los Angeles-Long Beach-Glendale (total)", "area",     False, "ca_subsectors.csv", "CA"),
    # United States (same supersector names, so California and the U.S. can be joined on name)
    ("PAYEMS",               "Total nonfarm",                        "total",       True,  "us_supersectors_sa.csv", "US"),
    ("USEHS",                "Private education & health services",  "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USLAH",                "Leisure & hospitality",                "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USTPU",                "Trade, transportation & utilities",    "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USGOVT",               "Government",                           "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USSERV",               "Other services",                       "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USMINE",               "Mining & logging",                     "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USCONS",               "Construction",                         "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USPBS",                "Professional & business services",     "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("MANEMP",               "Manufacturing",                        "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USFIRE",               "Financial activities",                 "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("USINFO",               "Information",                          "supersector", True,  "us_supersectors_sa.csv", "US"),
    ("CES6562000001",        "Health care & social assistance",      "subsector",   True,  "us_supersectors_sa.csv", "US"),
]

CA_METROS_FOCUS = [
    "Los Angeles-Long Beach-Anaheim, CA",
    "San Francisco-Oakland-Berkeley, CA",
    "San Jose-Sunnyvale-Santa Clara, CA",
    "San Diego-Chula Vista-Carlsbad, CA",
    "Riverside-San Bernardino-Ontario, CA",
    "Sacramento-Roseville-Folsom, CA",
]

# S&P 500 sector funds (SPDR Select Sector ETFs) and the closest BLS jobs sector.
# The match is approximate: stock sectors group companies by what they sell,
# jobs sectors group employers by what they do.
STOCKS = [
    # ticker, sector,                   closest jobs sector
    ("SPY",  "S&P 500 (all sectors)",   "Total nonfarm"),
    ("XLK",  "Technology",              "Information"),
    ("XLC",  "Communication services",  "Information"),
    ("XLV",  "Health care",             "Private education & health services"),
    ("XLF",  "Financials",              "Financial activities"),
    ("XLRE", "Real estate",             "Financial activities"),
    ("XLY",  "Consumer discretionary",  "Leisure & hospitality"),
    ("XLP",  "Consumer staples",        "Trade, transportation & utilities"),
    ("XLI",  "Industrials",             "Manufacturing"),
    ("XLB",  "Materials",               "Manufacturing"),
    ("XLE",  "Energy",                  "Mining & logging"),
    ("XLU",  "Utilities",               "Trade, transportation & utilities"),
]
