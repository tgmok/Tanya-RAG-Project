# What a good Tanya answer looks like

Honest note on timing: this was written on 2026-09-22, after the system and the evaluation
harness already existed, so it describes the bar the harness measures rather than a
prediction made in advance. It is still useful because each statement below is tied to a
check that can fail.

## Who this is for

From the problem statement: executive leadership and HQ executives at a diversified
conglomerate spanning F&B manufacturing, CNC machine parts manufacturing and gold jewellery, who
currently rely on delayed, manually compiled reports from each unit.

What changes once Tanya works: a cross-division issue, such as an F&B packaging change that needs
new CNC tooling, surfaces when a leader asks or when the document is filed, not at the next weekly
report. If nothing changes for them, the problem is not real.

## Five testable statements

| # | A good answer... | Checked by | Where it fails today |
|---|---|---|---|
| 1 | states the specific fact asked for (a number, id or date), not a summary | key-fact check against `data/eval_key_facts.json` (code) | 85% of the 20 pass in the final run: CD11 and CD12 miss a key fact, CD9 is handed to a person (`results/summary.md`) |
| 2 | names the document(s) it used, and only documents it was actually given | citation check (code) | four answers cite a document they were not given: CD2, CD11 and S4, and CD12 cites one that does not exist |
| 3 | for a cross-division question, is built from evidence in every division involved | document recall in `results/retrieval_recall.md` (code) | the shipped retrieval misses a needed document on 1 of 37 scored questions (CD12's `jwl-02`, two links away); 5 before reference-following |
| 4 | says exactly "The documents do not say." when the corpus is silent, and invents nothing | out-of-scope abstention (code) | none: 3 of 3 out-of-scope questions declined |
| 5 | does not hide behind abstention when the notes do contain the answer | over-abstain rate (code) | one answerable question handed to a person (CD9) although its documents were retrieved: the 0.45 threshold's one false alarm |

Statements 3 and 5 pull against each other: retrieving more chunks helps 3 and can
lengthen every prompt. The cost side of that trade is in `results/cost_estimate.md` (free) and
`results/cost_model.md` (after a live run).
