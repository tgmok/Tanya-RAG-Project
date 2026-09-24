# Blind question pack

**For whoever writes the questions (a classmate, or a different model in a fresh session).**

Below are 18 internal documents from a fictional conglomerate. Do not use any outside knowledge. Write questions ONLY from these documents.

Write exactly 6 questions:

1. Three that need facts from documents in at least two different divisions (`fnb-`, `cnc-`, `jwl-`).
2. Two that need only one division.
3. One that the documents do NOT answer but sounds like they might.

For each, give the answer you found and 1-3 short exact phrases from the documents that any correct answer must contain (numbers, ids and dates are best). Reply as JSON in exactly this shape:

```json
{"questions": [
  {"id": "IND1", "kind": "cross_division", "question": "...", "expected_divisions": ["fnb", "cnc"],
   "source_doc_ids": ["fnb-01", "cnc-01"], "groups": [["exact phrase", "alternative wording"], ["another fact"]],
   "why": "one line on what this tests"},
  {"id": "IND6", "kind": "out_of_scope", "question": "...", "expected_divisions": [], "source_doc_ids": [], "groups": [], "why": "..."}
]}
```

Each inner list in `groups` is one required fact; list alternative wordings inside it. Save the JSON as `data/independent_questions.json`, then run `python self_test.py` (it checks every fact appears in the cited documents) and `python run_eval.py --run`.

---

## DOCUMENT fnb-01

# SOP-FNB-014 — Packaging Specification Change Procedure

**Division:** F&B Contract Manufacturing (TGMOK Holdings)
**Effective:** 2026-06-01 · **Owner:** Packaging Engineering, F&B

## Purpose
Governs how a client-requested change to bottle, cap, or carton specification is evaluated,
approved, and rolled out on the production line.

## Procedure
1. Client Services logs the requested change in the Packaging Change Register within 1 business
   day of receipt.
2. Packaging Engineering assesses whether the change is compatible with existing filling and
   capping tooling. **Any change to cap diameter, thread pitch, or bottle neck finish requires new
   tooling from the CNC division** — the existing filling-line tooling cannot be re-machined
   on-site and must be replaced via a CNC work order.
3. If new tooling is required, Packaging Engineering raises a CNC Tooling Request (form
   CNC-TR-01) and the change is held at "pending tooling" status until CNC confirms a delivery
   date.
4. Once tooling is confirmed, a pilot run of 500 units is completed and inspected against
   QC-FNB-002 before full-line rollout.
5. Client sign-off is required before the new packaging appears on any shipped order.

## Recent example
Client Aurora Beverages (contract AB-2231) requested a narrower bottle neck for their sparkling
line in May 2026 to reduce material cost. Cap diameter changed from 28mm to 26mm, which changed
the thread pitch — this triggered a CNC Tooling Request (CNC-TR-01, logged 2026-05-14) since the
existing capping head could not accommodate the new thread without replacement tooling.

## Escalation
A packaging change that is not accompanied by a CNC Tooling Request when required must not
proceed to pilot run. Any line supervisor may halt a pilot run pending confirmation.

---

## DOCUMENT fnb-02

# Client Contract Summary — Aurora Beverages (AB-2231)

**Division:** F&B Contract Manufacturing (TGMOK Holdings)
**Contract term:** 2025-11-01 to 2027-10-31 · **Account owner:** Client Services, F&B

## Order profile
Aurora Beverages contracts TGMOK's F&B division to fill and package their sparkling water
line. Baseline order volume is 40,000 units/month across two SKUs.

## Rush order — June 2026
Aurora placed a rush order of 120,000 additional units for a retail promotion window
(2026-06-20 to 2026-07-05), triple the standard monthly volume. Meeting this volume on the
existing filling line schedule was not possible without additional machined parts for a second
capping head.

Client Services flagged the rush order to Production Planning on 2026-06-02. Because the
required capping-head components are machined by the CNC division rather than purchased
externally, Production Planning submitted a capacity request to CNC the same day so that CNC
could reprioritise its machining schedule ahead of the promotion window.

## Packaging
Standard packaging per SOP-FNB-014. No specification change was requested alongside this rush
order — this is a volume increase only, using the post-May-2026 26mm neck/cap tooling already in
place.

## Payment terms
Net 45, invoiced monthly. Rush-order units are invoiced at a 12% premium per the contract's
surge-capacity clause (Section 7.2).

---

## DOCUMENT fnb-03

# QC-FNB-002 — Filling Line Pilot Run Inspection Checklist

**Division:** F&B Contract Manufacturing (TGMOK Holdings)
**Applies to:** Any pilot run following a packaging or tooling change (see SOP-FNB-014)

## Checklist (500-unit pilot run)
1. Fill volume within ±1.5% of target across a 30-unit random sample.
2. Cap torque within 8-12 in-lb, measured on a 30-unit random sample.
3. Neck-to-cap seal integrity: submerge 10 units for 24 hours, zero leaks tolerated.
4. Label alignment within 2mm of specification on 100% visual inspection.
5. Carton drop test (1m, 3 orientations) on 5 units — no product breakage.
6. Batch code and best-before date legible and correct on 100% of sampled units.

## Sign-off
All six checks must pass before the batch record is marked "cleared for full-line rollout."
A failed check on items 1-3 requires the tooling to be re-inspected by the machine's
maintenance owner before a second pilot run is attempted — see the filling-line maintenance log.

## Record retention
Completed checklists are retained for 3 years and are the primary evidence reviewed during an
external client audit of the production line.

---

## DOCUMENT fnb-04

# Maintenance Log — Filling Line 2, Capping Head Assembly

**Division:** F&B Contract Manufacturing (TGMOK Holdings)
**Asset:** FL2-CAP-01 · **Owner:** Facilities Maintenance, F&B

## Entries

**2026-05-16** — Capping head disassembled to fit the new 26mm tooling delivered by CNC
(work order CNC-WO-0442) following the Aurora Beverages neck/cap change. Reassembly and
calibration completed same day. Torque tested against QC-FNB-002 item 2, passed at 10.1 in-lb
average.

**2026-05-28** — Routine lubrication and belt tension check. No faults found.

**2026-06-10** — Second capping head (FL2-CAP-02) installed ahead of the Aurora rush order to
support parallel-line filling. Machined components sourced from CNC work order CNC-WO-0458,
delivered 2026-06-08 — six days ahead of the requested date due to CNC's capacity
reprioritisation for the rush order.

**2026-06-22** — Mid-run inspection during the rush-order promotion window. No downtime
recorded. Both capping heads within tolerance.

## Open items
None outstanding as of this log's last entry.

---

## DOCUMENT fnb-05

# SOP-FNB-003 — Hygiene and Sanitation (HACCP-aligned)

**Division:** F&B Contract Manufacturing (TGMOK Holdings)
**Effective:** 2025-01-01 (annual review) · **Owner:** Quality Assurance, F&B

## Critical control points
1. **Incoming ingredient inspection** — temperature-logged on arrival; any deviation >2°C from
   spec is rejected and logged in the Non-Conformance Register.
2. **Filling line sanitation** — full CIP (clean-in-place) cycle every 8 hours of continuous
   operation, or immediately after any product changeover.
3. **Personnel hygiene** — hairnets, gloves, and hand sanitisation on entry; no exceptions for
   visitors, including divisional leadership walkthroughs.
4. **Pest control** — monthly third-party inspection, records retained 3 years.
5. **Allergen changeover** — any changeover between an allergen-containing and allergen-free
   product requires full line teardown and swab-test verification before restart.

## Non-conformance handling
A non-conformance at any control point halts the affected line until Quality Assurance signs
off on corrective action. This SOP does not distinguish by client or order priority — a rush
order does not exempt a line from a required CIP cycle or swab test.

## Audit trail
All checklists under this SOP are retained alongside QC-FNB-002 pilot-run records for combined
external audit review.

---

## DOCUMENT fnb-06

# F&B Division — Financial Summary, Q3 FY2026

**Division:** F&B Contract Manufacturing (TGMOK Holdings)
**Period:** 2026-07-01 to 2026-09-30 · **Prepared by:** Finance, F&B

## Revenue
Q3 revenue: $2.14M, up 18% quarter-on-quarter, driven largely by the Aurora Beverages rush-order
premium (Section 7.2 surge clause) and two new mid-size client contracts onboarded in August.

## Capital expenditure
The second capping head installed in June 2026 (FL2-CAP-02, see Maintenance Log) was funded
through an intercompany working-capital facility extended by the Jewellery division rather than
external financing, per the Group's Q2 treasury decision to keep short-notice capacity
expansions off the F&B division's own credit line. Facility amount: $180,000, drawn in full,
repayment scheduled over 18 months at the Group's internal transfer rate.

## Outlook
Q4 guidance assumes the Aurora relationship remains at rush-order-adjusted baseline volume
(not the full 120,000-unit spike) and that no further intercompany drawdowns are required
before the FY2027 capital budget cycle.

## Risk note
The division's reliance on jewellery-division financing for capacity expansion is flagged for
Group Treasury review — three divisions with materially different cash-flow cycles sharing one
internal lending facility is a concentration risk noted in the Q3 review meeting minutes.

---

## DOCUMENT cnc-01

# Tooling Spec — CNC-TR-01 (Capping Head, 26mm Neck/Cap)

**Division:** CNC Precision Machine Parts (TGMOK Holdings)
**Work order:** CNC-WO-0442 · **Requested by:** F&B Packaging Engineering
**Received:** 2026-05-14 · **Delivered:** 2026-05-16

## Requirement
F&B division requested new capping-head tooling to support a change from 28mm to 26mm bottle
neck/cap diameter for client Aurora Beverages (contract AB-2231). The diameter change altered
thread pitch, which meant the existing capping head could not be adapted — a new machined
capping-head assembly was required rather than a recalibration.

## Machining spec
- Material: hardened tool steel, grade per TGMOK CNC material standard MS-07
- Tolerance: ±0.02mm on thread pitch, ±0.05mm on head diameter
- Surface finish: Ra 0.4 μm on all contact surfaces
- Quantity: 1 unit, expedited (48-hour turnaround from standard 5-day lead time)

## Delivery
Delivered to F&B Facilities Maintenance 2026-05-16, within the 48-hour expedited window agreed
at intake. Installed same day per the F&B maintenance log (asset FL2-CAP-01).

## Follow-on order
A second unit of the same spec was ordered under CNC-WO-0458 (received 2026-06-08) to support a
parallel filling line ahead of an F&B rush order — see CNC Capacity Planning Report for the
scheduling impact of this follow-on request.

---

## DOCUMENT cnc-02

# CNC Capacity Planning Report — June 2026

**Division:** CNC Precision Machine Parts (TGMOK Holdings)
**Prepared by:** Production Planning, CNC · **Period covered:** 2026-06-01 to 2026-06-30

## Reprioritisation event
On 2026-06-02, Production Planning received an urgent capacity request from F&B Production
Planning to expedite machining of a second capping-head assembly (CNC-WO-0458), needed to
support an Aurora Beverages rush order (120,000 units, promotion window 2026-06-20 to
2026-07-05).

To meet the request, CNC reallocated approximately 22 machine-hours from a lower-priority
external client order (Order #C-4471, non-TGMOK client, precision bracket components) to the
CNC-WO-0458 job. The external order's delivery was pushed back 4 business days as a result; the
external client was notified and accepted the revised date without penalty clause invocation.

## Delivery outcome
CNC-WO-0458 was completed and delivered 2026-06-08, six days ahead of F&B's originally
requested date, allowing the second capping head to be installed and tested well before the
promotion window opened.

## Capacity note for Q3
This is the second instance in FY2026 of an F&B rush order requiring mid-cycle CNC
reprioritisation. Production Planning recommends F&B Client Services flag rush-order
possibilities at contract signing rather than at order placement, to avoid repeat impact on
external client schedules.

---

## DOCUMENT cnc-03

# Calibration Log — CNC Mill 3 (5-axis)

**Division:** CNC Precision Machine Parts (TGMOK Holdings)
**Asset:** CNC-M3 · **Owner:** Equipment Maintenance, CNC

## Entries

**2026-04-02** — Quarterly calibration. Positional accuracy within ±0.01mm across all axes.
Passed.

**2026-05-15** — Unscheduled calibration check ahead of expedited work order CNC-WO-0442
(capping-head tooling for F&B). Tolerance verified at ±0.02mm requirement before machining
began, per client-specified tolerance in the tooling spec.

**2026-06-07** — Unscheduled calibration check ahead of CNC-WO-0458 (second capping-head unit).
Passed within tolerance.

**2026-07-02** — Quarterly calibration. Spindle runout slightly elevated (0.008mm vs 0.005mm
baseline); flagged for bearing inspection at next scheduled maintenance window, not urgent.

## Notes
Unscheduled checks are triggered automatically for any work order with a stated tolerance
tighter than ±0.03mm, regardless of which division requested the part.

---

## DOCUMENT cnc-04

# POL-CNC-005 — Raw Material Procurement Policy

**Division:** CNC Precision Machine Parts (TGMOK Holdings)
**Effective:** 2025-03-01 · **Owner:** Procurement, CNC

## Approved suppliers
Tool steel, aluminium billet, and brass stock are sourced only from suppliers on the Approved
Vendor List (AVL), reviewed annually. Off-AVL purchases require Division Head sign-off and are
logged in the Procurement Exceptions Register.

## Minimum order and lead times
- Tool steel (grade MS-07 and MS-09): 5-day standard lead time, expedited to 48 hours available
  at a 30% surcharge for orders under 10 units.
- Aluminium billet: 3-day standard lead time.
- Brass stock: 7-day standard lead time, no expedited option — used primarily for jewellery
  division tooling and fixtures, which are planned on a longer cycle.

## Inventory buffer
CNC maintains a rolling 2-week buffer of MS-07 tool steel specifically to absorb expedited
internal work orders (e.g. from F&B) without disrupting external client lead times.

## Cost pass-through
Material costs for internal work orders (F&B, Jewellery) are charged at cost plus a 5% handling
fee via intercompany billing, distinct from the margin applied to external client orders.

---

## DOCUMENT cnc-05

# SOP-CNC-002 — Machine Shop Safety Procedure

**Division:** CNC Precision Machine Parts (TGMOK Holdings)
**Effective:** 2024-11-01 (annual review) · **Owner:** Health & Safety, CNC

## Mandatory PPE
Safety glasses, steel-toe boots, and hearing protection (mills and lathes generating >85dB) at
all times on the shop floor. No exceptions for short visits, including client walkthroughs.

## Lockout-tagout
Any unscheduled calibration or maintenance on an active mill requires lockout-tagout procedure
LOTO-01 before work begins, regardless of how urgent the requesting work order is. An expedited
internal request (e.g. same-day tooling for another division) does not waive this step.

## Incident reporting
Any near-miss or incident is logged within 24 hours in the Safety Incident Register, reviewed
monthly by Health & Safety with a summary sent to Division Head.

## Training
All machine operators complete safety recertification annually; a lapsed certification bars an
operator from running a 5-axis mill until recertified, even under production pressure.

---

## DOCUMENT cnc-06

# Client Order Backlog — CNC Division, June 2026 Snapshot

**Division:** CNC Precision Machine Parts (TGMOK Holdings)
**Prepared by:** Production Planning, CNC

## External orders
| Order | Client | Component | Status | Notes |
|---|---|---|---|---|
| C-4471 | (external, non-TGMOK) | Precision bracket components | Delayed 4 days | Reprioritised to accommodate internal work order CNC-WO-0458 (see Capacity Planning Report) |
| C-4488 | (external, non-TGMOK) | Custom shaft couplings | On schedule | No impact from internal reprioritisation |
| C-4502 | (external, non-TGMOK) | Housing plates, batch of 200 | On schedule | New order, received 2026-06-18 |

## Internal (intercompany) orders
| Work order | Requesting division | Component | Status |
|---|---|---|---|
| CNC-WO-0442 | F&B | Capping head, 26mm | Delivered 2026-05-16 |
| CNC-WO-0458 | F&B | Capping head, 26mm (second unit) | Delivered 2026-06-08 |
| CNC-WO-0470 | Jewellery | Custom stamping die | In progress, due 2026-07-10 |

## Notes
Internal work orders are prioritised above external orders only when explicitly flagged urgent
by the requesting division's Production Planning lead, per POL-CNC-005's exceptions process.

---

## DOCUMENT jwl-01

# Intercompany Financing Report — Jewellery Division Treasury

**Division:** Gold Jewellery Manufacturing & Retail (TGMOK Holdings)
**Period:** FY2026 Q2-Q3 · **Prepared by:** Treasury, Jewellery Division

## Purpose
The Jewellery division holds the Group's largest cash reserve, owing to gold inventory
liquidity and retail cash flow. Per the Group's Q2 FY2026 treasury decision, the division
operates an internal working-capital facility that F&B and CNC can draw on for short-notice
capacity needs, rather than each division seeking external financing individually.

## Facilities extended
| Recipient | Amount | Purpose | Drawn | Repayment |
|---|---|---|---|---|
| F&B Division | $180,000 | Second capping-head line (FL2-CAP-02) for Aurora Beverages rush order | 2026-06 | 18 months, Group internal transfer rate |
| CNC Division | $45,000 | Buffer inventory of MS-07 tool steel to support expedited internal work orders | 2026-04 | 12 months, Group internal transfer rate |

## Rationale
Extending financing intercompany rather than through external lenders avoids interest-rate
markup and keeps capacity-expansion decisions inside the Group. It does concentrate liquidity
risk on the Jewellery division's balance sheet, which Group Treasury reviews quarterly.

## Governance note
Any single facility above $250,000 requires Group CFO sign-off in addition to Jewellery
Treasury approval. Both facilities above are below this threshold and were approved at
divisional level.

---

## DOCUMENT jwl-02

# POL-JWL-002 — Gold Pricing and Client Quotation Policy

**Division:** Gold Jewellery Manufacturing & Retail (TGMOK Holdings)
**Effective:** 2025-01-01 (reviewed quarterly) · **Owner:** Pricing, Jewellery Division

## Pricing basis
Client quotes are priced off the London Bullion Market Association (LBMA) AM fix on the day of
quotation, plus a workmanship margin that varies by design complexity (12-28%) and a fixed
retail overhead allocation of 6%.

## Quote validity
A quotation is valid for 5 business days from issue, given daily gold price volatility. A quote
not accepted within this window must be re-priced against the current fix before order
confirmation.

## Custom stamping dies
Custom pieces requiring a new stamping die are quoted with an additional one-time tooling
charge, sourced from a CNC division work order (see Client Order Backlog, CNC-WO-0470 series)
rather than an external toolmaker, per the Group's intercompany sourcing preference for
tooling under $10,000.

## Discount authority
Discounts up to 5% may be approved by a retail store manager; discounts above 5% require
Division Head approval and are logged in the Discount Exceptions Register.

---

## DOCUMENT jwl-03

# SOP-JWL-006 — Precious Metal Inventory Audit Procedure

**Division:** Gold Jewellery Manufacturing & Retail (TGMOK Holdings)
**Effective:** 2024-06-01 (audited quarterly) · **Owner:** Inventory Control, Jewellery Division

## Audit cycle
Full physical count of raw gold stock, work-in-progress, and finished retail inventory every
quarter, reconciled against the perpetual inventory system within 48 hours of count completion.

## Custody controls
- Raw gold stock: dual-custody access, two authorised staff required to open the vault.
- Work-in-progress: tracked by job ticket from casting through polishing; any piece unaccounted
  for at a stage transition triggers an immediate investigation, not a quarterly-cycle wait.
- Finished retail inventory: reconciled daily at each retail location against point-of-sale
  records.

## Variance thresholds
A variance beyond 0.1% of gold weight at any custody point requires Division Head notification
within 24 hours and a root-cause report within 5 business days.

## Relationship to Treasury
Reconciled inventory values feed directly into the Jewellery division's liquidity reporting,
which in turn determines available headroom on the intercompany financing facility described in
the Treasury's intercompany financing report.

---

## DOCUMENT jwl-04

# SOP-JWL-009 — Gold Purity Certification Procedure

**Division:** Gold Jewellery Manufacturing & Retail (TGMOK Holdings)
**Effective:** 2023-09-01 · **Owner:** Quality Assurance, Jewellery Division

## Certification requirement
Every finished piece above $500 retail value is tested for gold purity (karat) using an
X-ray fluorescence (XRF) analyser before it is released to retail stock. Results are logged
against the piece's job ticket.

## Hallmarking
Pieces meeting certification are stamped with the TGMOK hallmark and karat value. A piece
failing certification is quarantined and routed back to Production for investigation — it may
not be re-tested and released without a documented cause.

## Custom stamping dies
Hallmark stamping dies are themselves precision components; replacement or new-design dies are
sourced via CNC division work order, following the same tooling-request process as other
divisions' machined parts.

## Record retention
Certification records are retained for 7 years, in line with retail warranty obligations on
purity claims.

---

## DOCUMENT jwl-05

# POL-JWL-011 — Retail Returns and Exchange Policy

**Division:** Gold Jewellery Manufacturing & Retail (TGMOK Holdings)
**Effective:** 2025-02-01 · **Owner:** Retail Operations, Jewellery Division

## Standard terms
Unworn pieces with original certification may be returned within 14 days for a full refund, or
exchanged within 30 days for store credit at current gold-fix valuation.

## Custom pieces
Custom-designed pieces (including any requiring a new stamping die per SOP-JWL-009) are
final sale and not eligible for return, disclosed to the client in writing at quotation stage
per POL-JWL-002.

## Resizing
One complimentary resizing is included within 60 days of purchase for standard (non-custom)
rings. Additional resizing is charged at a flat workmanship fee.

## Fraud controls
Any return above $2,000 retail value requires the original XRF certification record to be
matched against the returned piece before refund is processed, to prevent substitution.

---

## DOCUMENT jwl-06

# Client Quote — Job JWL-Q-3391 (Custom Commission)

**Division:** Gold Jewellery Manufacturing & Retail (TGMOK Holdings)
**Client:** Private commission (name withheld, retail confidentiality) · **Issued:** 2026-06-25

## Design brief
18-karat gold pendant, custom engraved motif, requiring a new stamping die (motif not in
existing die library).

## Quote breakdown
| Item | Amount |
|---|---|
| Gold (18k, 12g) at LBMA AM fix 2026-06-25 | $912.40 |
| Workmanship (custom complexity, 22%) | $200.73 |
| Retail overhead allocation (6%) | $66.79 |
| Custom stamping die tooling charge (CNC work order) | $850.00 |
| **Total** | **$2,029.92** |

## Validity
Quote valid 5 business days from issue (2026-06-30), per POL-JWL-002. Gold component will be
re-priced against the current fix if the client accepts after this window.

## Terms
This is a custom piece: final sale on completion, no return eligibility, per POL-JWL-011.
Client acknowledged this in writing at quotation, 2026-06-25.

---
