# Data dictionary — Tanya's document corpus

18 documents, 6 per division, all under `data/<division>/`. Every document is synthetic
(generated per `generation_prompts.md`) but structurally realistic: an id/reference number, an
owner, and dated entries, mirroring what a real internal SOP or report looks like.

| id | division | file | doc type | carries hook(s) |
|---|---|---|---|---|
| fnb-01 | F&B | `fnb/packaging_change_sop.md` | SOP | H1 |
| fnb-02 | F&B | `fnb/client_contract_summary.md` | contract summary | H3 |
| fnb-03 | F&B | `fnb/quality_control_checklist.md` | QC checklist | — |
| fnb-04 | F&B | `fnb/maintenance_log.md` | maintenance log | H1, H3 |
| fnb-05 | F&B | `fnb/hygiene_sop.md` | SOP | — |
| fnb-06 | F&B | `fnb/financial_summary_q3.md` | financial report | H2 |
| cnc-01 | CNC | `cnc/tooling_spec_bottle_cap.md` | tooling spec | H1 |
| cnc-02 | CNC | `cnc/capacity_planning_report.md` | capacity report | H2, H3 |
| cnc-03 | CNC | `cnc/machine_calibration_log.md` | calibration log | — |
| cnc-04 | CNC | `cnc/material_procurement_policy.md` | policy | — |
| cnc-05 | CNC | `cnc/safety_sop.md` | SOP | — |
| cnc-06 | CNC | `cnc/client_order_backlog.md` | order backlog | H3 |
| jwl-01 | Jewellery | `jewellery/finance_intercompany_loan_report.md` | financial report | H2 |
| jwl-02 | Jewellery | `jewellery/gold_pricing_policy.md` | policy | — |
| jwl-03 | Jewellery | `jewellery/inventory_audit_sop.md` | SOP | — |
| jwl-04 | Jewellery | `jewellery/quality_certification_sop.md` | SOP | — |
| jwl-05 | Jewellery | `jewellery/retail_returns_policy.md` | policy | — |
| jwl-06 | Jewellery | `jewellery/client_quote_template.md` | client quote | — |

## Cross-division hooks (ground truth, fixed before generation)

- **H1** — An F&B packaging spec change requires new CNC tooling. Carried by `fnb-01`, `fnb-04`,
  `cnc-01`.
- **H2** — Jewellery division extends intercompany financing to F&B and CNC. Carried by `jwl-01`,
  `fnb-06`, `cnc-02`.
- **H3** — An F&B rush order forces CNC to reallocate machining capacity. Carried by `fnb-02`,
  `fnb-04`, `cnc-02`, `cnc-06`.

A correct answer to a cross-division question naming hook H*n* must draw on chunks from **every**
division listed for that hook — this is what `eval_questions.json`'s `expected_divisions` field
checks, and what the context-recall metric in the problem statement (Section 7) measures.
