# Leakage check (no model, no cost)

Does the question already contain the answer it is graded on? Two kinds are checked: **question-side** (a key fact the answer is scored on is already stated in the question, so `key_fact_check` could pass on the asker's words) and **retrieval-side** (the question repeats the source document's wording, so retrieval is string matching). For every leaky question the leaked phrases are deleted and recall is re-scored -- the before/after gap is what those copied words were carrying.

Config: `naive_k5`. Scored questions examined: 31. With at least one leaked key fact: **5** (16%).

On the leaky questions only, document recall 100% before stripping -> 90% after; division recall 100% -> 100%.
Across all scored questions, document recall 92% -> 91%.

| id | set | leaked groups / total | leaked phrases | doc recall before -> after | division recall before -> after |
|---|---|---|---|---|---|
| S3 | main | 2/2 | `lockout`, `urgent`, `waive` | 100% -> 100% | True -> True |
| CD7 | main | 1/2 | `rush` | 100% -> 100% | True -> True |
| S2 | main | 1/2 | `concentration` | 100% -> 100% | True -> True |
| S4 | main | 1/2 | `calibration` | 100% -> 50% | True -> True |
| IND1 | independent | 1/2 | `new tooling` | 100% -> 100% | True -> True |

Stripped questions, for inspection:

- **CD7**: `What did CNC Production Planning recommend to avoid repeat impact on external clients from future F&B orders?`
- **S2**: `What risk did Group Treasury flag in the F&B Q3 financial summary?`
- **S3**: `Does an internal tooling request CNC's -tagout requirement?`
- **S4**: `What tolerance was required for work order CNC-WO-0442, and was a check done before machining began?`
- **IND1**: `Why did Aurora Beverages’ change from a 28mm to a 26mm bottle neck require involvement from both the F&B and CNC divisions, and which CNC work order was used for the ?`
