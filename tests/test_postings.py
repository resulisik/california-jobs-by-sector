"""Checks for the keyword rules in src/postings.py.  Run: python tests/test_postings.py (or pytest)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from postings import eng_type_of, family_of, location_of, norm_title, seniority_of  # noqa: E402

FAMILY = [
    ("Data Analyst", "T", "Data & analytics"), ("Senior Data Scientist, Growth", "T", "Data & analytics"),
    ("Analytics Engineer", "F", "Data & analytics"), ("Software Engineer - Data Platform", "T", "Software engineering & IT"),
    ("Technical Product Manager II, Data Platforms", "T", "Product & design"), ("Business Intelligence Developer", "H", "Data & analytics"),
    ("Machine Learning Engineer", "T", "AI & machine learning"), ("Research Scientist, Oncology", "H", "Science & research"),
    ("Research Scientist, Pretraining", "T", "AI & machine learning"), ("Registered Nurse (RN)", "H", "Health care (clinical)"),
    ("Product Manager, Pharmacy", "H", "Product & design"), ("Software Engineer, Backend", "F", "Software engineering & IT"),
    ("Sales Engineer", "T", "Sales & customer success"), ("Account Executive, Mid-Market", "T", "Sales & customer success"),
    ("Propulsion Engineer", "A", "Hardware & other engineering"), ("Engineer, Payments", "F", "Software engineering & IT"),
    ("Engineer, Launch Operations", "A", "Hardware & other engineering"), ("Senior Accountant", "C", "Finance & accounting"),
    ("Recruiter", "T", "People, legal & admin"), ("Video Editor", "M", "Creative & media production"),
    ("Lead Gameplay Programmer", "M", "Software engineering & IT"), ("Personal Trainer, West 76th Street", "C", "Operations, service & supply chain"),
    ("Warehouse Associate", "C", "Operations, service & supply chain"), ("Brand Marketing Manager", "C", "Marketing & communications"),
]
SENIORITY = [
    ("Data Analyst I", "Entry level"), ("Junior Data Analyst", "Entry level"), ("Software Engineer, New Grad", "Entry level"),
    ("Associate Product Manager", "Entry level"), ("Associate Director, Finance", "Senior & management"),
    ("Senior Data Analyst", "Senior & management"), ("Data Analyst II", "Senior & management"),
    ("Engineering Manager", "Senior & management"), ("Account Manager", "Mid or not stated"),
    ("Data Analyst", "Mid or not stated"), ("Software Engineering Intern, Summer 2027", "Internship"),
    ("Account Executive", "Mid or not stated"), ("CPU Verification Fellow", "Mid or not stated"),
]
LOCATION = [
    ("Los Angeles, CA", "Los Angeles area"), ("El Segundo, California, United States", "Los Angeles area"),
    ("Irvine, California, United States", "Los Angeles area"), ("San Francisco", "Other California"),
    ("San Francisco, CA; Seattle, WA; New York, NY; Los Angeles, CA", "Los Angeles area"),
    ("Remote - USA", "Remote (U.S.)"), ("New York, NY (Remote)", "Other U.S."), ("Austin, TX", "Other U.S."),
    ("London, England", "Outside U.S."), ("Bengaluru; Gurugram; Mumbai", "Outside U.S."), ("Berlin, DE", "Outside U.S."),
    ("Toronto, CA", "Outside U.S."), ("Remote - Sweden", "Outside U.S."), ("Hybrid", "Not stated"),
    ("Remote", "Remote (country not stated)"), ("Northlake IL", "Other U.S."), ("Mohali, IND", "Outside U.S."),
]


def test_family():
    for title, sector, want in FAMILY:
        assert family_of(title, sector) == want, (title, family_of(title, sector), want)


def test_seniority():
    for title, want in SENIORITY:
        assert seniority_of(title) == want, (title, seniority_of(title), want)


def test_location():
    for loc, want in LOCATION:
        got = location_of(loc, "", "", "")["loc_bucket"]
        assert got == want, (loc, got, want)


def test_misc():
    assert eng_type_of("Senior Mechanical Engineer") == "Mechanical"
    assert eng_type_of("Data Analyst") == ""
    assert norm_title("Senior Data Analyst, Marketing (Remote)") == "Data Analyst"
    assert norm_title("Senior Manager, Finance") == "Manager, Finance"
    assert norm_title("Operations Associate, Tulsa") == "Operations Associate"


if __name__ == "__main__":
    bad = [(t, family_of(t, s), w) for t, s, w in FAMILY if family_of(t, s) != w]
    bad += [(t, seniority_of(t), w) for t, w in SENIORITY if seniority_of(t) != w]
    bad += [(loc, location_of(loc, "", "", "")["loc_bucket"], w) for loc, w in LOCATION
            if location_of(loc, "", "", "")["loc_bucket"] != w]
    for b in bad:
        print("FAIL", b)
    test_misc()
    print("all postings tests passed" if not bad else f"{len(bad)} failed")
    sys.exit(1 if bad else 0)
