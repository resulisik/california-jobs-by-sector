"""Download the raw data.

BLS employment series come from FRED (St. Louis Fed), which republishes the
BLS Current Employment Statistics. Job postings come from Indeed Hiring Lab's
public GitHub repository.

Usage:  python src/download_data.py          (skips files that already exist)
        python src/download_data.py --force  (re-downloads everything)
"""
import io
import sys

import pandas as pd
import requests

from config import FRED_CSV, INDEED_FILES, INDEED_RAW, RAW_BLS, RAW_INDEED, SERIES


def fetch(url: str) -> bytes:
    r = requests.get(url, timeout=120, headers={"User-Agent": "ca-sector-jobs/1.0"})
    r.raise_for_status()
    return r.content


def download_bls(force: bool) -> None:
    RAW_BLS.mkdir(parents=True, exist_ok=True)
    by_file: dict[str, list[str]] = {}
    for sid, _name, _level, _sa, fname in SERIES:
        by_file.setdefault(fname, []).append(sid)

    for fname, ids in by_file.items():
        out = RAW_BLS / fname
        if out.exists() and not force:
            print(f"skip  {out.name} (exists)")
            continue
        merged = None
        for sid in ids:
            df = pd.read_csv(io.BytesIO(fetch(FRED_CSV.format(series=sid))))
            df.columns = ["date", sid]
            df = df[df["date"] >= "2020-01-01"]
            merged = df if merged is None else merged.merge(df, on="date", how="outer")
        merged.sort_values("date").to_csv(out, index=False)
        print(f"saved {out.name}: {len(merged)} rows, {len(ids)} series")


def download_indeed(force: bool) -> None:
    RAW_INDEED.mkdir(parents=True, exist_ok=True)
    for fname, path in INDEED_FILES.items():
        out = RAW_INDEED / fname
        if out.exists() and not force:
            print(f"skip  {out.name} (exists)")
            continue
        out.write_bytes(fetch(INDEED_RAW.format(path=path)))
        print(f"saved {out.name}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    failed = False
    for step in (download_bls, download_indeed):
        try:
            step(force)
        except requests.RequestException as exc:
            failed = True
            print(f"FAILED {step.__name__}: {exc}")
    sys.exit(1 if failed else 0)
