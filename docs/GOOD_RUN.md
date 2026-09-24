# What a good Tanya answer looks like

Honest note on timing: this was written on 2026-09-22, after the system and the evaluation
harness already existed, so it describes the bar the harness measures rather than a
prediction made in advance. It is still useful because each statement below is tied to a
check that can fail.

## Who this is for (DRAFT: edit before you rely on it)

> Priya, TGMOK Holdings' Group COO, on her phone at 8:40am before a 9am leadership call. A new
> client brief has just been forwarded to her. She knows each division's headline numbers but
> has never opened another division's SOPs, and she does not want a paragraph: she wants to
> know what else moves before she walks into the room.

What she does differently once Tanya works: she raises the tooling lead time and the
financing question **on the call**, not after the next weekly report. If nothing changes for
her, the problem in Section 2 is not real. Replace this with a person or role you know
better, then copy the line into Section 3 of the problem statement.

## Five testable statements

| # | A good answer... | Checked by | Where it fails today |
|---|---|---|---|
| 1 | states the specific fact asked for (a number, id or date), not a summary | key-fact check against `data/eval_key_facts.json` (code) | 80% of the 20 pass: CD4, CD11 and CD12 miss a key fact, CD3 declines (`results/notebook_run.md`) |
| 2 | names the document(s) it used, and only documents it was actually given | citation check (code) | same |
| 3 | for a cross-division question, is built from evidence in every division involved | document recall in `results/retrieval_recall.md` (code) | the shipped retrieval misses a needed document on 4 of 31 scored questions; 3 of the 4 are the same CNC tooling spec (`cnc-01`) |
| 4 | says exactly "The documents do not say." when the corpus is silent, and invents nothing | out-of-scope abstention (code) | none: 3 of 3 out-of-scope questions declined |
| 5 | does not hide behind abstention when the notes do contain the answer | over-abstain rate (code) | one answerable question declined (CD3), and its needed document had not been retrieved |

Statements 3 and 5 pull against each other: retrieving more chunks helps 3 and can
lengthen every prompt. The cost side of that trade is in `results/cost_estimate.md` (free) and
`results/cost_model.md` (after a live run).
