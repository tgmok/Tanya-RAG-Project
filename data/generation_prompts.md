# Generation prompts — committed per the watch-outs ("treat the generator as part of your system")

Fixed **before** any document was written, so the cross-division hooks are ground truth,
not something discovered after looking at outputs.

## Cross-division hooks (fixed first)

| Hook | Divisions | Documents that carry it |
|---|---|---|
| H1 | F&B → CNC | An F&B packaging spec change requires new CNC tooling | `fnb/fnb-01_packaging_change_sop.md`, `cnc/cnc-01_tooling_spec_bottle_cap.md` |
| H2 | Jewellery → F&B, CNC | Jewellery division extends intercompany financing to the other two divisions | `jewellery/jwl-01_finance_intercompany_loan_report.md`, `fnb/fnb-06_financial_summary_q3.md`, `cnc/cnc-02_capacity_planning_report.md` |
| H3 | F&B → CNC | An F&B rush order causes CNC to reallocate machining capacity | `fnb/fnb-02_client_contract_summary.md`, `cnc/cnc-02_capacity_planning_report.md` |

Each hook is deliberately split across **two or three documents in different divisions**, so a
single-division retrieval can only ever answer half the question — this is what the metric
"context recall: did Tanya retrieve chunks from every division a cross-division query touches"
metric is built to catch.

## Per-document generation prompt template

Each document was produced with a prompt of this shape (model: a general-purpose chat LLM,
temperature low, one document per call):

```
You are writing an internal [SOP | financial report | client contract summary | maintenance log |
quality checklist | policy document] for the [F&B contract manufacturing | CNC precision machine
parts | gold jewellery] division of a fictional conglomerate called TGMOK Holdings.

Write it in the plain, slightly dry register of a real internal document — no marketing language.
Length: 150-300 words. Include concrete, checkable details: names, dates, quantities, ids.

It MUST include this fact, stated plainly, not as a headline: "<hook fact>"

Do not resolve or reference other divisions' internal reasoning — only state the fact from this
division's point of view, as it would actually be recorded.
```

`<hook fact>` was filled in from the hooks table above, once per hook, for each document that
carries it — this fixes the ground truth before generation, per the data guidance in the
course watch-outs.

## Regenerating

To regenerate a document: take its row from `data_dictionary.md`, plug its hook fact (if any)
into the template above, and run it through the same model. Re-running should not change which
facts are present, only their wording — that stability is what makes `eval_questions.json` a
durable answer key rather than a moving target.
