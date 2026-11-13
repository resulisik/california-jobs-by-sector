"""Paths and series definitions shared by every script."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_BLS = ROOT / "data" / "raw" / "bls"
RAW_INDEED = ROOT / "data" / "raw" / "indeed"
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "ca_jobs.db"
SQL_DIR = ROOT / "sql"
CHARTS = ROOT / "charts"
DOCS = ROOT / "docs"

# Analysis window: 5 years ending in the latest month BLS has published.
START_MONTH = "2021-09-01"
END_MONTH = "2026-09-01"
PRE_PANDEMIC = "2020-02-01"

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2020-01-01"
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
    # id,                    name,                                   level,         sa,    file
    ("CANA",                 "Total nonfarm",                        "total",       True,  "ca_supersectors_sa.csv"),
    ("CAEDUH",               "Private education & health services",  "supersector", True,  "ca_supersectors_sa.csv"),
    ("CALEIH",               "Leisure & hospitality",                "supersector", True,  "ca_supersectors_sa.csv"),
    ("CATRAD",               "Trade, transportation & utilities",    "supersector", True,  "ca_supersectors_sa.csv"),
    ("CAGOVT",               "Government",                           "supersector", True,  "ca_supersectors_sa.csv"),
    ("CASRVO",               "Other services",                       "supersector", True,  "ca_supersectors_sa.csv"),
    ("CANRMN",               "Mining & logging",                     "supersector", True,  "ca_supersectors_sa.csv"),
    ("CACONS",               "Construction",                         "supersector", True,  "ca_supersectors_sa.csv"),
    ("CAPBSV",               "Professional & business services",     "supersector", True,  "ca_supersectors_sa.csv"),
    ("CAMFG",                "Manufacturing",                        "supersector", True,  "ca_supersectors_sa.csv"),
    ("CAFIRE",               "Financial activities",                 "supersector", True,  "ca_supersectors_sa.csv"),
    ("SMS06000005000000001", "Information",                          "supersector", True,  "ca_subsectors.csv"),
    ("SMS06000006562000001", "Health care & social assistance",      "subsector",   True,  "ca_subsectors.csv"),
    ("SMS06000006054000001", "Professional, scientific & technical", "subsector",   True,  "ca_subsectors.csv"),
    ("SMS06000004300000001", "Transportation, warehousing & utilities", "subsector",   True,  "ca_subsectors.csv"),
    ("SMS06000004200000001", "Retail trade",                         "subsector",   True,  "ca_subsectors.csv"),
    ("SMS06000007072000001", "Accommodation & food services",        "subsector",   True,  "ca_subsectors.csv"),
    ("SMU06000003133640001", "Aerospace product & parts",            "subsector",   False, "ca_subsectors.csv"),
    ("SMU06000005051200001", "Motion picture & sound recording",     "subsector",   False, "ca_subsectors.csv"),
    ("SMU06000006054150001", "Computer systems design",              "subsector",   False, "ca_subsectors.csv"),
    ("SMU06310840000000001", "Los Angeles-Long Beach-Glendale (total)", "area",     False, "ca_subsectors.csv"),
]

CA_METROS_FOCUS = [
    "Los Angeles-Long Beach-Anaheim, CA",
    "San Francisco-Oakland-Berkeley, CA",
    "San Jose-Sunnyvale-Santa Clara, CA",
    "San Diego-Chula Vista-Carlsbad, CA",
    "Riverside-San Bernardino-Ontario, CA",
    "Sacramento-Roseville-Folsom, CA",
]
