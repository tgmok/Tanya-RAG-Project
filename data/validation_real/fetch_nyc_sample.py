"""Reproduce the real-world validation sample in nyc_inspections.md.

Pulls live from NYC Open Data's Socrata API (dataset 43nn-pn8j, "DOHMH New York City
Restaurant Inspection Results") -- the same underlying dataset Kaggle's NYC Restaurant
Inspections mirror is built from. No API key needed; standard library only.

Committed per the same discipline as generation_prompts.md: the pull is part of the
system, so a reader can reproduce or refresh this sample rather than trusting a static
file with no visible provenance. Re-running this will likely return a DIFFERENT sample
(the live dataset keeps growing) -- that's expected. The 8 records actually used and
hand-checked in validation_questions.json are the ones already committed in
nyc_inspections.md; re-running this script is for refreshing the slice later, not for
reproducing today's exact output bit-for-bit.
"""
import json
import random
import urllib.parse
import urllib.request

BASE = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"


def fetch_sample(n=8, seed=7, since="2025-01-01"):
    params = {
        "$where": (
            f"violation_description IS NOT NULL AND inspection_date > '{since}' "
            "AND critical_flag != 'Not Applicable' AND boro IS NOT NULL"
        ),
        "$limit": "500",
        "$order": "inspection_date DESC",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    records = json.load(urllib.request.urlopen(req, timeout=30))

    random.seed(seed)
    random.shuffle(records)

    seen_dba = set()
    diverse = []
    for r in records:
        dba, desc = r.get("dba"), r.get("violation_description")
        if not dba or not desc or dba in seen_dba:
            continue
        seen_dba.add(dba)
        diverse.append(r)
        if len(diverse) >= n:
            break
    return diverse


if __name__ == "__main__":
    sample = fetch_sample()
    print(f"fetched {len(sample)} diverse records")
    for r in sample:
        print(f"{r['dba']} | {r['boro']} | {r['inspection_date'][:10]} | "
              f"{r['violation_code']} | {r['critical_flag']}")
