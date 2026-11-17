"""Collect a new job-postings snapshot from public job APIs.

Usage:  python src/collect_postings.py            -> data/raw/postings/postings_<today>.csv.gz
Then set POSTINGS_SNAPSHOT in src/config.py to the new date and run build_database.py.

Sources (all public, no key needed):
  - Applicant tracking systems that serve company careers pages: Greenhouse, Ashby, Lever,
    SmartRecruiters. The employers are listed in data/research/postings_boards.csv.
  - Remote job boards: Remotive, Remote OK and Jobicy. Their terms ask you to credit them and
    link back to each posting; the url column does that.

For postings whose title looks data-related, the description is read and only two things are kept:
which skills it names (SQL, Python, Tableau ...) and the first advertised pay range. Descriptions
themselves are not stored.

The snapshot of 17 Nov 2026 in this repository was collected with the same requests from a browser.
"""
import gzip
import html
import io
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pandas as pd
import requests

from config import RAW_POSTINGS, RESEARCH

COLUMNS = ["source", "slug", "company", "sector", "job_id", "title", "department", "location", "location_extra", "remote",
           "country", "region", "employment_type", "experience_level", "posted_at", "url", "desc_fetched", "skills",
           "pay_min", "pay_max", "pay_period"]
DATA_RE = re.compile(r"\b(data|analytics?|analyst|business intelligence|bi|insights?|reporting|statistic\w*"
                     r"|machine learning|scientist|quantitative|quant)\b", re.I)
SKILLS = {
    "sql": r"\bsql\b", "python": r"\bpython\b", "excel": r"\bexcel\b", "tableau": r"\btableau\b",
    "power_bi": r"\bpower\s?bi\b", "looker": r"\blooker\b", "dbt": r"\bdbt\b", "snowflake": r"\bsnowflake\b",
    "bigquery": r"\bbigquery\b", "aws": r"\baws\b|amazon web services", "spark": r"\bspark\b", "airflow": r"\bairflow\b",
    "statistics": r"statistic", "ab_testing": r"\bA/B\b|experimentation", "machine_learning": r"machine learning|\bML\b",
}
SKILL_RE = {k: re.compile(v, re.I) for k, v in SKILLS.items()}
SKILL_RE["r"] = re.compile(r"\b(R|RStudio)\b(?![&'’-])")  # case-sensitive
PAY_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?\s?[kK]?)\s*(?:USD|usd)?\s*(?:-|–|—|to)\s*\$?\s?"
                    r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?\s?[kK]?)")
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "sector-pulse/1.0 (portfolio project)"


def get_json(url):
    for attempt in range(3):
        r = SESSION.get(url, timeout=60)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code != 200:
            return None
        return r.json()
    return None


def text_of(html_text):
    t = html.unescape(html.unescape(html_text or ""))
    return re.sub(r"<[^>]+>", " ", t)


def skills_and_pay(text):
    skills = "|".join(k for k, rx in SKILL_RE.items() if rx.search(text or ""))
    m = PAY_RE.search(text or "")
    if not m:
        return skills, "", "", ""

    def val(s):
        s = re.sub(r"[,\s]", "", s)
        x = float(s.rstrip("kK"))
        return x * 1000 if s[-1:] in "kK" else x
    a, b = val(m.group(1)), val(m.group(2))
    if not (a > 0 and b >= a):
        return skills, "", "", ""
    period = "hour" if b < 500 else "year"
    if period == "year" and (a < 15000 or b > 2_000_000):
        return skills, "", "", ""
    return skills, a, b, period


def row(**kw):
    r = dict.fromkeys(COLUMNS, "")
    r["desc_fetched"] = 0
    r.update(kw)
    return r


def add_description(r, text):
    if DATA_RE.search(r["title"]):
        r["desc_fetched"] = 1
        r["skills"], r["pay_min"], r["pay_max"], r["pay_period"] = skills_and_pay(text)
    return r


def greenhouse(slug, company, sector):
    j = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/departments")
    if not j:
        return []
    out, seen = [], set()

    def walk(depts):
        for d in depts or []:
            for jb in d.get("jobs", []):
                if jb["id"] in seen:
                    continue
                seen.add(jb["id"])
                out.append(row(source="greenhouse", slug=slug, company=company, sector=sector, job_id=jb["id"],
                               title=jb.get("title", ""), department=d.get("name", ""),
                               location=(jb.get("location") or {}).get("name", ""),
                               posted_at=jb.get("first_published") or jb.get("updated_at", ""),
                               url=jb.get("absolute_url", "")))
            walk(d.get("children"))
    walk(j.get("departments"))
    for r in out:
        if DATA_RE.search(r["title"]):
            d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{r['job_id']}") or {}
            add_description(r, text_of(d.get("content")))
    return out


def ashby(slug, company, sector):
    j = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    out = []
    for jb in (j or {}).get("jobs", []):
        if jb.get("isListed") is False:
            continue
        pa = ((jb.get("address") or {}).get("postalAddress")) or {}
        comp = jb.get("compensation") or {}
        r = row(source="ashby", slug=slug, company=company, sector=sector, job_id=jb.get("id"), title=jb.get("title", ""),
                department=" / ".join(x for x in (jb.get("department"), jb.get("team")) if x),
                location=jb.get("location", ""), location_extra=" | ".join(x.get("location", "") for x in jb.get("secondaryLocations") or []),
                remote="1" if jb.get("isRemote") else (jb.get("workplaceType") or ""), country=pa.get("addressCountry", ""),
                region=pa.get("addressRegion", ""), employment_type=jb.get("employmentType", ""),
                posted_at=jb.get("publishedAt", ""), url=jb.get("jobUrl", ""))
        out.append(add_description(r, (comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary") or "")
                                   + "\n" + (jb.get("descriptionPlain") or "")))
    return out


def lever(slug, company, sector):
    j = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for jb in j if isinstance(j, list) else []:
        c = jb.get("categories") or {}
        sr = jb.get("salaryRange") or {}
        created = jb.get("createdAt")
        r = row(source="lever", slug=slug, company=company, sector=sector, job_id=jb.get("id"), title=jb.get("text", ""),
                department=" / ".join(x for x in (c.get("department"), c.get("team")) if x), location=c.get("location", ""),
                location_extra=" | ".join(c.get("allLocations") or []), remote=jb.get("workplaceType", ""),
                country=jb.get("country", ""), employment_type=c.get("commitment", ""),
                posted_at=datetime.fromtimestamp(created / 1000, timezone.utc).isoformat() if created else "",
                url=jb.get("hostedUrl", ""))
        lists = " ".join(f"{x.get('text', '')} {text_of(x.get('content'))}" for x in jb.get("lists") or [])
        pay = f"${sr['min']} - ${sr['max']}" if sr.get("min") else ""
        out.append(add_description(r, "\n".join([pay, jb.get("descriptionPlain") or "", lists, jb.get("additionalPlain") or ""])))
    return out


def smartrecruiters(slug, company, sector):
    out, offset = [], 0
    while True:
        j = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}&country=us")
        if not j:
            break
        for p in j.get("content", []):
            loc = p.get("location") or {}
            r = row(source="smartrecruiters", slug=slug, company=company, sector=sector, job_id=p.get("id"), title=p.get("name", ""),
                    department=((p.get("department") or {}).get("label") or (p.get("function") or {}).get("label") or ""),
                    location=", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x),
                    remote="1" if loc.get("remote") else "", country=loc.get("country", ""), region=loc.get("region", ""),
                    employment_type=(p.get("typeOfEmployment") or {}).get("label", ""),
                    experience_level=(p.get("experienceLevel") or {}).get("label", ""), posted_at=p.get("releasedDate", ""),
                    url=f"https://jobs.smartrecruiters.com/{slug}/{p.get('id')}")
            if DATA_RE.search(r["title"]):
                d = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{p.get('id')}") or {}
                sections = ((d.get("jobAd") or {}).get("sections")) or {}
                add_description(r, "\n".join(text_of(s.get("text")) for s in sections.values()))
            out.append(r)
        offset += 100
        if not j.get("content") or offset >= j.get("totalFound", 0) or offset >= 2000:
            break
    return out


def remote_boards():
    out = []
    j = get_json("https://remotive.com/api/remote-jobs") or {}
    for x in j.get("jobs", []):
        r = row(source="remotive", slug="remotive", company=x.get("company_name", ""), sector="R", job_id=x.get("id"),
                title=x.get("title", ""), department=x.get("category", ""), location=x.get("candidate_required_location", ""),
                remote="1", employment_type=x.get("job_type", ""), posted_at=x.get("publication_date", ""), url=x.get("url", ""))
        out.append(add_description(r, f"{x.get('salary', '')} {text_of(x.get('description'))}"))
    j = get_json("https://remoteok.com/api") or []
    for x in j:
        if not (isinstance(x, dict) and x.get("id") and x.get("position")):
            continue
        r = row(source="remoteok", slug="remoteok", company=x.get("company", ""), sector="R", job_id=x["id"], title=x["position"],
                department=" / ".join((x.get("tags") or [])[:4]), location=x.get("location", ""), remote="1",
                posted_at=x.get("date", ""), url=x.get("url", ""))
        pay = f"${x['salary_min']} - ${x['salary_max']}" if x.get("salary_min") else ""
        out.append(add_description(r, f"{pay} {text_of(x.get('description'))}"))
    seen = set()
    for ind in ["", "data-science", "dev", "engineering", "finance", "healthcare", "marketing", "management",
                "design-multimedia", "admin", "accounting", "hr", "sales", "supporting", "technical-support", "copywriting", "business"]:
        j = get_json("https://jobicy.com/api/v2/remote-jobs?count=50&geo=usa" + (f"&industry={ind}" if ind else "")) or {}
        for x in j.get("jobs", []):
            if x.get("id") in seen:
                continue
            seen.add(x.get("id"))
            r = row(source="jobicy", slug="jobicy", company=x.get("companyName", ""), sector="R", job_id=x.get("id"),
                    title=x.get("jobTitle", ""), department=" / ".join(x.get("jobIndustry") or []), location=x.get("jobGeo", ""),
                    remote="1", employment_type=" / ".join(x.get("jobType") or []), experience_level=x.get("jobLevel", ""),
                    posted_at=x.get("pubDate", ""), url=x.get("url", ""))
            pay = f"${x['annualSalaryMin']} - ${x['annualSalaryMax']}" if x.get("annualSalaryMin") else ""
            out.append(add_description(r, f"{pay} {text_of(x.get('jobDescription') or x.get('jobExcerpt'))}"))
        time.sleep(0.5)
    return out


def main() -> int:
    boards = pd.read_csv(RESEARCH / "postings_boards.csv")
    fetch = {"greenhouse": greenhouse, "ashby": ashby, "lever": lever, "smartrecruiters": smartrecruiters}
    rows = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for part in pool.map(lambda b: fetch[b.platform](b.slug, b.company, b.sector), boards.itertuples()):
            rows.extend(part)
    rows.extend(remote_boards())
    df = pd.DataFrame(rows, columns=COLUMNS)
    RAW_POSTINGS.mkdir(parents=True, exist_ok=True)
    out = RAW_POSTINGS / f"postings_{date.today().isoformat()}.csv.gz"
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    with gzip.open(out, "wt", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"{len(df):,} postings from {df['company'].nunique()} companies -> {out}")
    return 0 if len(df) else 1


if __name__ == "__main__":
    sys.exit(main())
