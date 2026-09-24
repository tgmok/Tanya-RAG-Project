"""Reproduce the CNC real-world validation sample in cnc_industrial_safety.md.

Pulls the IHM Stefanini "Industrial Safety and Health Analytics Database" from its
author's public GitHub mirror (no Kaggle login needed) and filters to the Metals
industry sector, picking one record per distinct Critical Risk category for variety.
Standard library only.

Same discipline as fetch_nyc_sample.py: committed so the sample is reproducible /
refreshable, not offered as a bit-for-bit guarantee (the mirror is a static CSV, so
re-running this WILL reproduce the same 8 rows, unlike the live NYC/OSHA APIs -- but
still worth keeping the fetch logic visible and versioned).
"""
import csv
import io
import json
import urllib.request

CSV_URL = ("https://raw.githubusercontent.com/theshreyansh/"
           "HS-E_Data_Analysis_IHM_Stefanini/master/"
           "HS-E_Data_Analysis_IHM_Stefanini.csv")


def fetch_sample(n=8, sector="Metals"):
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
    rows = list(csv.DictReader(io.StringIO(raw)))

    filtered = [r for r in rows if r["Industry Sector"] == sector and r["Description"].strip()]

    seen_risk = set()
    diverse = []
    for r in filtered:
        risk = r["Critical Risk"]
        if risk in seen_risk:
            continue
        seen_risk.add(risk)
        diverse.append(r)
        if len(diverse) >= n:
            break
    return diverse


if __name__ == "__main__":
    sample = fetch_sample()
    print(f"fetched {len(sample)} diverse records from Metals sector")
    for r in sample:
        print(f"{r['Data'][:10]} | {r['Critical Risk']} | {r['Employee or Third Party']}")
