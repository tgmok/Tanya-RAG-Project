# Real-world validation slice — NYC Restaurant Inspection Results

**Source:** NYC Open Data, "DOHMH New York City Restaurant Inspection Results"
(dataset id `43nn-pn8j`), fetched live from the Socrata API
(`https://data.cityofnewyork.us/resource/43nn-pn8j.json`) on 2026-09-14.
**Licence:** NYC Open Data — public government data, published under NYC's Open Data
terms of use (no copyright restriction on municipal inspection records).

**This file is NOT part of Tanya's main corpus.** It exists only for the
real-world validation check ("validate a handful of cases against something real, or
state plainly what your synthetic set cannot tell you"). Do not add cross-division hooks
here — these are real, independent records, unrelated to TGMOK Holdings.

8 real violation records, deliberately picked for variety (8 different establishments,
a mix of critical/non-critical flags, different violation types) rather than the most
recent records, which clustered on 2-3 establishments on a single inspection day.

---

## nyc-01 — SWEET SPOT (Queens)

- Inspection: 2026-09-09, Cycle Inspection / Initial Inspection
- Violation code: 06C · **Critical** · Grade: A · Score: 13
- Description: Food, supplies, or equipment not protected from potential source of
  contamination during storage, preparation, transportation, display, service or from
  customer's refillable, reusable container. Condiments not in single-service
  containers or dispensed directly by the vendor.

## nyc-02 — NEW YORK YACHT CLUB (Manhattan)

- Inspection: 2026-09-09, Cycle Inspection / Initial Inspection
- Violation code: 06C · **Critical** · Grade: A · Score: 13
- Description: Food, supplies, or equipment not protected from potential source of
  contamination during storage, preparation, transportation, display, service or from
  customer's refillable, reusable container. Condiments not in single-service
  containers or dispensed directly by the vendor.

## nyc-03 — VAN LEEUWEN ICE CREAM (Manhattan)

- Inspection: 2026-09-09, Cycle Inspection / Re-inspection
- Violation code: 04A · **Critical** · Grade: A · Score: 12
- Description: Food Protection Certificate (FPC) not held by manager or supervisor of
  food operations.

## nyc-04 — Q.C CAMPUS EATS / TAIWANESE YUMMY / PAN ASIAN FOOD (Queens)

- Inspection: 2026-09-09, Cycle Inspection / Reopening Inspection
- Violation code: 08A · Not Critical · Grade: (none recorded) · Score: 43
- Description: Establishment is not free of harborage or conditions conducive to
  rodents, insects or other pests.

## nyc-05 — DANTE APERITIVO (Manhattan)

- Inspection: 2026-09-08, Pre-permit (Operational) / Initial Inspection
- Violation code: 02G · **Critical** · Grade: N · Score: 40
- Description: Cold TCS food item held above 41°F; smoked or processed fish held above
  38°F; intact raw eggs held above 45°F; or reduced oxygen packaged (ROP) TCS foods
  held above required temperatures except during active necessary preparation.

## nyc-06 — ZHENGXIN CHICKEN STEAK (Queens)

- Inspection: 2026-09-08, Cycle Inspection / Initial Inspection
- Violation code: 10C · Not Critical · Grade: N · Score: 44
- Description: Lighting inadequate; permanent lighting not provided in food
  preparation areas, ware washing areas, and storage rooms. Shatterproof bulb or
  shield to prevent broken glass from falling into food or onto surfaces, not
  installed.

## nyc-07 — GAZALA'S (Manhattan)

- Inspection: 2026-09-09, Cycle Inspection / Re-inspection
- Violation code: 08A · Not Critical · Grade: Z · Score: 28
- Description: Establishment is not free of harborage or conditions conducive to
  rodents, insects or other pests.

## nyc-08 — TARTINERY (Manhattan)

- Inspection: 2026-09-09, Cycle Inspection / Initial Inspection
- Violation code: 08A · Not Critical · Grade: A · Score: 13
- Description: Establishment is not free of harborage or conditions conducive to
  rodents, insects or other pests.
