"""Download the raw data.

BLS employment series come from FRED (St. Louis Fed), which republishes the
BLS Current Employment Statistics. Job postings come from Indeed Hiring Lab's
public GitHub repository. Sector fund prices come from Yahoo Finance.
The files in data/research/ are collected by hand and are never downloaded.

Usage:  python src/download_data.py          (skips files that already exist)
        python src/download_data.py --force  (re-downloads everything)
"""
import io
import sys

import pandas as pd
import requests

from config import (FRED_CSV, FRED_YEARLY, INDEED_FILES, INDEED_RAW, INDEED_TRACKERS, RAW_BLS, RAW_INDEED, RAW_JOLTS,
                    RAW_STOCKS, RAW_TRACKERS, SERIES, STOCKS, YAHOO_CHART)


def fetch(url: str) -> bytes:
    r = requests.get(url, timeout=120, headers={"User-Agent": "ca-sector-jobs/1.0"})
    r.raise_for_status()
    return r.content


def download_bls(force: bool) -> None:
    RAW_BLS.mkdir(parents=True, exist_ok=True)
    by_file: dict[str, list[str]] = {}
    for sid, _name, _level, _sa, fname, _region in SERIES:
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


def download_stocks(force: bool) -> None:
    """Month-end adjusted close for each sector fund, from Yahoo Finance's chart endpoint."""
    import time
    from datetime import datetime, timezone

    RAW_STOCKS.mkdir(parents=True, exist_ok=True)
    out = RAW_STOCKS / "sector_etf_monthly.csv"
    if out.exists() and not force:
        print(f"skip  {out.name} (exists)")
        return
    p1 = int(datetime(2020, 12, 1, tzinfo=timezone.utc).timestamp())
    this_month = datetime.now(timezone.utc).strftime("%Y-%m")
    merged = None
    for ticker, _sector, _jobs in STOCKS:
        r = requests.get(YAHOO_CHART.format(ticker=ticker, p1=p1, p2=int(time.time())), timeout=60,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        df = pd.DataFrame({"ts": res["timestamp"], ticker: res["indicators"]["adjclose"][0]["adjclose"]})
        df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True)
        df = df[df["dt"].dt.day <= 2].dropna()          # monthly bars only, not the live quote
        df["month"] = df["dt"].dt.strftime("%Y-%m")
        df = df[df["month"] < this_month][["month", ticker]].round(3)   # complete months only
        merged = df if merged is None else merged.merge(df, on="month", how="outer")
    merged.sort_values("month").to_csv(out, index=False)
    print(f"saved {out.name}: {len(merged)} rows")


def download_jolts(force: bool) -> None:
    """JOLTS openings, hires, quits and layoffs, unemployed persons and the fed funds rate, from FRED."""
    RAW_JOLTS.mkdir(parents=True, exist_ok=True)
    out = RAW_JOLTS / "fred_jolts_2020_2026.csv"
    if out.exists() and not force:
        print(f"skip  {out.name} (exists)")
        return
    frames = []
    for sid, *_ in FRED_YEARLY:
        df = pd.read_csv(io.BytesIO(fetch(FRED_CSV.format(series=sid))))
        df.columns = ["date", "value"]
        df["series_id"] = sid
        frames.append(df[pd.to_numeric(df["value"], errors="coerce").notna()])
    pd.concat(frames)[["series_id", "date", "value"]].to_csv(out, index=False)
    print(f"saved {out.name}: {len(FRED_YEARLY)} series")


def download_trackers(force: bool) -> None:
    """Indeed Hiring Lab AI, remote-work and posted-wage trackers, U.S. rows only."""
    RAW_TRACKERS.mkdir(parents=True, exist_ok=True)
    for fname, url in INDEED_TRACKERS.items():
        out = RAW_TRACKERS / fname
        if out.exists() and not force:
            print(f"skip  {out.name} (exists)")
            continue
        df = pd.read_csv(io.BytesIO(fetch(url)))
        df[df["jobcountry"] == "US"].to_csv(out, index=False)
        print(f"saved {out.name}")


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
    for step in (download_bls, download_stocks, download_indeed, download_jolts, download_trackers):
        try:
            step(force)
        except requests.RequestException as exc:
            failed = True
            print(f"FAILED {step.__name__}: {exc}")
    sys.exit(1 if failed else 0)
