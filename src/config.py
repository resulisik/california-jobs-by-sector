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
RAW_POSTINGS = ROOT / "data" / "raw" / "postings"
RAW_JOLTS = ROOT / "data" / "raw" / "jolts"
RAW_TRACKERS = ROOT / "data" / "raw" / "trackers"
POSTINGS_SNAPSHOT = "2026-11-17"

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

# Fields used for the "top occupations" view, in display order.
OCCUPATION_FIELDS = {
    "engineering": "Engineering",
    "health": "Health care",
    "finance": "Finance",
    "computer": "Computer & data",
    "film": "Film & media",
}

# My grouping of the New York Fed's 73 majors into eight families.
MAJOR_GROUPS = {
    "Engineering & architecture": ["AEROSPACE ENGINEERING", "CHEMICAL ENGINEERING", "CIVIL ENGINEERING", "COMPUTER ENGINEERING",
        "ELECTRICAL ENGINEERING", "GENERAL ENGINEERING", "INDUSTRIAL ENGINEERING", "MECHANICAL ENGINEERING",
        "MISCELLANEOUS ENGINEERING", "ENGINEERING TECHNOLOGIES", "CONSTRUCTION SERVICES", "ARCHITECTURE"],
    "Computer & math": ["COMPUTER SCIENCE", "INFORMATION SYSTEMS & MANAGEMENT", "MATHEMATICS", "BUSINESS ANALYTICS",
        "MISCELLANEOUS TECHNOLOGIES"],
    "Business & finance": ["ACCOUNTING", "FINANCE", "ECONOMICS", "BUSINESS MANAGEMENT", "GENERAL BUSINESS", "MARKETING",
        "ADVERTISING AND PUBLIC RELATIONS", "LEISURE AND HOSPITALITY"],
    "Health": ["NURSING", "PHARMACY", "MEDICAL TECHNICIANS", "HEALTH SERVICES", "TREATMENT THERAPY", "NUTRITION SCIENCES"],
    "Education": ["EARLY CHILDHOOD EDUCATION", "ELEMENTARY EDUCATION", "GENERAL EDUCATION", "MISCELLANEOUS EDUCATION",
        "SECONDARY EDUCATION", "SPECIAL EDUCATION"],
    "Arts & media": ["FINE ARTS", "PERFORMING ARTS", "COMMERCIAL ART & GRAPHIC DESIGN", "MASS MEDIA", "JOURNALISM",
        "COMMUNICATIONS", "ART HISTORY"],
    "Natural sciences": ["BIOLOGY", "BIOCHEMISTRY", "CHEMISTRY", "PHYSICS", "EARTH SCIENCES", "ENVIRONMENTAL STUDIES",
        "MISCELLANEOUS BIOLOGICAL SCIENCE", "MISCELLANEOUS PHYSICAL SCIENCES", "ANIMAL AND PLANT SCIENCES", "AGRICULTURE"],
}
OTHER_MAJOR_GROUP = "Social sciences & humanities"


# Year-by-year view (Part 7). FRED series, monthly from 2020:
# (series_id, measure, industry, jobs_sector, seasonally_adjusted)
# FRED carries JOLTS industry detail only without seasonal adjustment, so industry openings are
# compared as annual averages (or the same months of two years), where seasonality cancels out.
FRED_YEARLY = [
    ("JTSJOL", "openings", "Total nonfarm", "Total nonfarm", 1),
    ("JTSHIL", "hires", "Total nonfarm", "Total nonfarm", 1),
    ("JTSQUL", "quits", "Total nonfarm", "Total nonfarm", 1),
    ("JTSLDL", "layoffs", "Total nonfarm", "Total nonfarm", 1),
    ("JTUJOL", "openings", "Total nonfarm", "Total nonfarm", 0),
    ("JTUHIL", "hires", "Total nonfarm", "Total nonfarm", 0),
    ("JTUQUL", "quits", "Total nonfarm", "Total nonfarm", 0),
    ("JTULDL", "layoffs", "Total nonfarm", "Total nonfarm", 0),
    ("JTU1000JOL", "openings", "Total private", "Total private", 0),
    ("JTU110099JOL", "openings", "Mining and logging", "Mining & logging", 0),
    ("JTU2300JOL", "openings", "Construction", "Construction", 0),
    ("JTU3000JOL", "openings", "Manufacturing", "Manufacturing", 0),
    ("JTU4000JOL", "openings", "Trade, transportation, and utilities", "Trade, transportation & utilities", 0),
    ("JTU5100JOL", "openings", "Information", "Information", 0),
    ("JTU510099JOL", "openings", "Financial activities", "Financial activities", 0),
    ("JTU540099JOL", "openings", "Professional and business services", "Professional & business services", 0),
    ("JTU6000JOL", "openings", "Private education and health services", "Private education & health services", 0),
    ("JTU6200JOL", "openings", "Health care and social assistance", "Private education & health services", 0),
    ("JTU7000JOL", "openings", "Leisure and hospitality", "Leisure & hospitality", 0),
    ("JTU8100JOL", "openings", "Other services", "Other services", 0),
    ("JTU9000JOL", "openings", "Government", "Government", 0),
    ("UNEMPLOY", "unemployed", "Unemployed persons (CPS)", "Total nonfarm", 1),
    ("FEDFUNDS", "fed_funds_rate", "Effective federal funds rate (%)", "", 0),
]
# Other Indeed Hiring Lab repositories (CC BY 4.0); only U.S. rows are kept.
INDEED_TRACKERS = {
    "ai_postings_share_US.csv": "https://raw.githubusercontent.com/hiring-lab/ai-tracker/main/AI_posting.csv",
    "remote_postings_share_US.csv": "https://raw.githubusercontent.com/hiring-lab/remote-tracker/main/remote_postings.csv",
    "posted_wage_growth_US.csv": "https://raw.githubusercontent.com/hiring-lab/indeed-wage-tracker/main/posted-wage-growth-by-country.csv",
}
