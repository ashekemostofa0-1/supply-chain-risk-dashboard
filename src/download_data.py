"""Step 5: download one source per indicator into data/raw/ (files are saved untouched).

Run from the project folder:
    python -m src.download_data

What it downloads (6 NAICS industries from src/config.py, 2019-2024):

  Indicator            Source (saved under data/raw/)
  -------------------  ---------------------------------------------------------
  Shipments, payroll,  census_asm/   Annual Survey of Manufactures, 2019-2021
  employees, fuel and  census_ec/    2022 Economic Census (replaces ASM that year)
  electricity cost     census_aies/  Annual Integrated Economic Survey, 2023-2024
  Imports / exports    census_trade/ Census international trade API, by NAICS
  Price volatility     fred_ppi/     FRED Producer Price Index by industry (monthly)
  Validation target    fred_ip/      FRED Industrial Production by industry (monthly)

Every download is logged (URL, file, date, status) in data/raw/download_log.csv,
and the same table is written into the "Data sources" section of README.md.
A failed download is logged and skipped, so one outage never stops the whole run.
"""

import csv
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from src.config import INDUSTRIES, YEARS, RAW_DIR

# The Census API now requires a free key: https://api.census.gov/data/key_signup.html
# Save it in a file named census_api_key.txt in the project folder (git ignores that
# file, so the key never goes to GitHub), or set $env:CENSUS_API_KEY in PowerShell.
def _read_key():
    if os.environ.get("CENSUS_API_KEY"):
        return os.environ["CENSUS_API_KEY"].strip()
    if os.path.exists("census_api_key.txt"):
        with open("census_api_key.txt", encoding="utf-8") as f:
            return f.read().strip()
    return ""


CENSUS_KEY = _read_key()

CENSUS = "https://api.census.gov/data"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="

# FRED Producer Price Index by industry: one series per NAICS code
PPI_SERIES = {naics: f"PCU{naics}{naics}" for naics in INDUSTRIES}

# FRED Industrial Production (Federal Reserve G.17). Two industries have no
# exact 4-digit series, so the closest published aggregate is used:
#   3241 -> NAICS 324 (3241 is the only industry group inside 324)
#   3259 -> NAICS 3255,9 (paints + other chemical products)
IP_SERIES = {
    "3241": "IPG324S",
    "3251": "IPG3251S",
    "3252": "IPG3252S",
    "3253": "IPG3253S",
    "3259": "IPG3255A9S",
    "3261": "IPG3261S",
}

LOG_FIELDS = ["indicator", "source", "naics", "year", "file", "url", "downloaded", "status"]


def fetch(url):
    """Return the response body as bytes (raises on HTTP or network errors)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (student research project)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def census_url(dataset, params):
    params = dict(params)
    if CENSUS_KEY:
        params["key"] = CENSUS_KEY
    return f"{CENSUS}/{dataset}?" + urllib.parse.urlencode(params, safe=",:*")


def build_jobs():
    """List every file to download as (indicator, source, naics, year, relative path, url)."""
    jobs = []
    for naics in INDUSTRIES:
        # Census ASM, 2019-2021: shipments, payroll, employees, electricity, fuels
        for year in [y for y in YEARS if y <= 2021]:
            url = census_url("timeseries/asm/area2017", {
                "get": "NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU",
                "for": "us:*", "YEAR": year, "NAICS2017": naics})
            jobs.append(("shipments/energy/labor", "Census ASM", naics, year,
                         f"census_asm/asm_{naics}_{year}.json", url))

        # 2022 Economic Census (no ASM in census years)
        if 2022 in YEARS:
            url = census_url("2022/ecnbasic", {
                "get": "NAICS2022_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU",
                "for": "us:*", "NAICS2022": naics})
            jobs.append(("shipments/energy/labor", "Census Economic Census 2022", naics, 2022,
                         f"census_ec/ec_{naics}_2022.json", url))

        # AIES, 2023 onward: revenue, payroll, employees (basic) + energy costs (exp02)
        for year in [y for y in YEARS if y >= 2023]:
            url = census_url(f"{year}/aiesbasic", {
                "get": "NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM",
                "for": "us:*", "YEAR": year, "NAICS2017": naics})
            jobs.append(("shipments/labor", "Census AIES basic", naics, year,
                         f"census_aies/aies_basic_{naics}_{year}.json", url))
            url = census_url(f"{year}/aiesexp02", {
                "get": "NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL",
                "for": "us:*", "YEAR": year, "NAICS2017": naics})
            jobs.append(("energy", "Census AIES expenses", naics, year,
                         f"census_aies/aies_exp_{naics}_{year}.json", url))

        # International trade by NAICS: December year-to-date = full-year total
        for year in YEARS:
            url = census_url("timeseries/intltrade/imports/naics", {
                "get": "NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR",
                "time": f"{year}-12", "NAICS": naics})
            jobs.append(("import dependence", "Census trade: imports", naics, year,
                         f"census_trade/imports_{naics}_{year}.json", url))
            url = census_url("timeseries/intltrade/exports/naics", {
                "get": "NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR",
                "time": f"{year}-12", "NAICS": naics})
            jobs.append(("import dependence", "Census trade: exports", naics, year,
                         f"census_trade/exports_{naics}_{year}.json", url))

        # FRED monthly series (full history; the cleaning step trims the years)
        sid = PPI_SERIES[naics]
        jobs.append(("price volatility", "FRED PPI by industry", naics, "all",
                     f"fred_ppi/{sid}.csv", FRED_CSV + sid))
        sid = IP_SERIES[naics]
        jobs.append(("validation target", "FRED Industrial Production", naics, "all",
                     f"fred_ip/{sid}.csv", FRED_CSV + sid))
    return jobs


def update_readme(rows, readme="README.md"):
    """Rewrite the Data sources section of README.md from the download log."""
    start, end = "<!-- SOURCES START -->", "<!-- SOURCES END -->"
    table = ["| Indicator | Source | NAICS | Year | File | Downloaded | Status |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        link = f"[{r['file']}]({r['url'].split('&key=')[0]})"
        table.append(f"| {r['indicator']} | {r['source']} | {r['naics']} | {r['year']} | "
                     f"{link} | {r['downloaded']} | {r['status']} |")
    section = (f"{start}\n## Data sources\n\nRaw files in `data/raw/` are saved exactly as "
               f"downloaded by `python -m src.download_data`. Each file name links to its "
               f"source URL.\n\n" + "\n".join(table) + f"\n{end}")
    with open(readme, encoding="utf-8") as f:
        text = f.read()
    if start in text and end in text:
        text = text[:text.index(start)] + section + text[text.index(end) + len(end):]
    else:
        text = text.rstrip() + "\n\n" + section + "\n"
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    today = dt.date.today().isoformat()
    if not CENSUS_KEY:
        print("WARNING: no Census API key found, so Census downloads will fail.")
        print("Get a free key at https://api.census.gov/data/key_signup.html and save it")
        print("in census_api_key.txt in the project folder, then run this again.\n")
    jobs = build_jobs()
    rows, failed = [], 0
    print(f"Downloading {len(jobs)} files into {RAW_DIR}/ ...")
    for i, (indicator, source, naics, year, rel, url) in enumerate(jobs, 1):
        path = os.path.join(RAW_DIR, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            body = fetch(url)
            if not body.strip():
                raise ValueError("empty response (no data for this industry/year)")
            if "api.census.gov" in url:
                try:
                    data = json.loads(body)
                except ValueError:
                    raise ValueError("not data: Census sent a web page (check your API key)")
                if not isinstance(data, list) or len(data) < 2:
                    raise ValueError("no rows returned")
            with open(path, "wb") as f:
                f.write(body)
            status = "ok"
        except (urllib.error.URLError, ValueError, TimeoutError, OSError) as e:
            code = getattr(e, "code", "")
            # Census returns HTTP 204 / empty body when a value is suppressed or missing
            status = f"missing ({code or e})"[:80]
            failed += 1
            if os.path.exists(path):
                os.remove(path)  # never keep a bad or outdated file in data/raw
        rows.append({"indicator": indicator, "source": source, "naics": naics, "year": year,
                     "file": f"data/raw/{rel}", "url": url, "downloaded": today, "status": status})
        print(f"[{i:3}/{len(jobs)}] {status:<10} {rel}")
        time.sleep(0.2)  # be polite to the APIs

    log_path = os.path.join(RAW_DIR, "download_log.csv")
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({**r, "url": r["url"].split("&key=")[0]})
    update_readme(rows)
    print(f"\nDone: {len(jobs) - failed} downloaded, {failed} missing.")
    print(f"Log: {log_path}   README.md 'Data sources' section updated.")


if __name__ == "__main__":
    main()
