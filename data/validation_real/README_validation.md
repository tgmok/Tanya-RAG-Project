# Real-world validation slices (Section 6)

Answers the watch-outs' Section 6 requirement: *"validate a handful of cases against
something real, or state plainly what your synthetic set cannot tell you."* One small
slice per division, kept separate from the main corpus.

## Status

| Division | Slice | Status |
|---|---|---|
| F&B | NYC restaurant inspections | Done |
| CNC | Industrial Safety and Health Analytics Database (Metals sector) | Done |
| Jewellery | eCommerce purchase history from jewelry store | Done -- different shape, see below |

## What's here

```
nyc_inspections.md              8 real NYC restaurant inspection violation records
fnb_validation_questions.json   3 in-scope + 1 out-of-scope question for the F&B slice
fetch_nyc_sample.py             the pull (live Socrata API, no auth needed)

cnc_industrial_safety.md        8 real industrial accident records, Metals sector
cnc_validation_questions.json   3 in-scope + 1 out-of-scope question for the CNC slice
fetch_cnc_sample.py             the pull (static CSV mirror, no auth needed)

jewellery_retail_transactions.md   8 real transactions + a price-distribution table
jewellery_validation_questions.json 3 in-scope + 1 out-of-scope question for jewellery
build_jewellery_sample.py       reproduces the sample/table from your own jewelry.csv
                                 (raw file NOT committed -- see Jewellery section below)
```

## F&B — source and provenance

Pulled live from NYC Open Data's Socrata API for the "DOHMH New York City Restaurant
Inspection Results" dataset (id `43nn-pn8j`) on 2026-09-14 -- the same underlying data
Kaggle's NYC Restaurant Inspections listing mirrors. Public government data under NYC
Open Data's terms of use; no licence restriction on reuse of municipal inspection
records. The 8 records were deliberately chosen for establishment variety (8 different
restaurants, a mix of critical/non-critical violations, several violation types) rather
than taking the single most recent batch, which clustered on 2-3 establishments from
one inspection day.

## CNC — source and provenance

IHM Stefanini's "Industrial Safety and Health Analytics Database" -- real accident
records from 12 manufacturing/industrial plants across 3 countries. Listed on Kaggle at
`kaggle.com/datasets/ihmstefanini/industrial-safety-and-health-analytics-database`, but
fetched here from the dataset author's own public GitHub mirror
(`github.com/theshreyansh/HS-E_Data_Analysis_IHM_Stefanini`) since this environment has
no Kaggle credentials -- same data, different host, no login required. Filtered to the
**Metals** industry sector (the dataset's three sectors are Mining, Metals, Others),
the closest real-world match to CNC precision machining, and picked one record per
distinct Critical Risk category for variety.

## Jewellery — source and provenance

"eCommerce purchase history from jewelry store" (Michael Kechinov / REES46),
`kaggle.com/datasets/mkechinov/ecommerce-purchase-history-from-jewelry-store` --
95,911 real transactions from an actual online jewellery retailer (Dec 2018 - Feb 2019).
No public mirror exists (checked the author's own site, rees46.com/en/datasets -- it
only links back to Kaggle), so this one was downloaded by you directly from Kaggle
rather than pulled programmatically.

**The raw `jewelry.csv` (~13.6MB, 95,911 rows) is deliberately NOT committed to this
repo** -- per the watch-outs' Section 6 guidance for data you can't freely redistribute:
"ship trained weights, a small sample, and a README that says exactly this." Only the
hand-picked 8-row sample and the aggregate price-distribution table (computed from the
full file) are committed, in `jewellery_retail_transactions.md`.
`build_jewellery_sample.py` reproduces both from your own local copy of `jewelry.csv`
if you (or a marker) want to verify them independently -- confirmed to reproduce the
committed numbers exactly.

**This slice is a different shape than the other two**, and that's stated explicitly in
`jewellery_retail_transactions.md`: it's real transaction data (product, price,
category, metal, gem), not narrative document text -- so it validates *pricing
plausibility* (`jewellery/gold_pricing_policy.md`, `jewellery/client_quote_template.md`)
rather than whether TGMOK's jewellery SOPs read like real internal documents. One
concrete finding worth keeping in your write-up: TGMOK's example custom quote
($2,029.92) sits well above the real median gold-pendant price ($136.85) -- expected
given it's a bespoke commission with a die-tooling charge, but worth naming as a
limitation of the synthetic example rather than treating it as a typical price point.

## Why these are kept separate from the main corpus

`data/fnb/`, `data/cnc/`, `data/jewellery/` are TGMOK Holdings' designed corpus with
fixed cross-division hooks and a matching answer key (`eval_questions.json`) -- adding
real, unrelated records into that set would break the hook design with no plan for how
they fit. These slices exist only to answer one narrow question per division: **does
Tanya's retrieval and grounding hold up on real, messier text, not just the clean
synthetic SOPs it was designed around?** Run the same chunk -> embed -> retrieve ->
grounded-answer -> judge pipeline from the main notebook against each slice, using its
own validation-questions file as the answer key, and report the faithfulness/abstention
numbers here side by side with the main corpus numbers.

## Known limits (applies to every slice here)

- 8 records per division is enough to make the point, not enough for a statistically
  meaningful score -- report each as a spot-check, not a second eval set.
- These are single-fact records (one incident/violation each), so they don't test
  cross-division-style multi-document synthesis the way `eval_questions.json`'s
  cross-division questions do. They test faithfulness and abstention on unfamiliar,
  real text -- a narrower, complementary check.
- The NYC slice is a live-API pull; re-running `fetch_nyc_sample.py` will return a
  DIFFERENT sample than the one committed (the dataset keeps growing). The CNC slice is
  a static-CSV pull; re-running `fetch_cnc_sample.py` reproduces the same 8 rows. Both
  scripts exist so the pull logic is visible and versioned, not as a reproducibility
  guarantee in the NYC case.
