# Answer-level evaluation

Generation `openai/gpt-4o-mini`; judge `google/gemini-2.5-flash` (a different model family from the generator). Run 2026-09-25. Embedder: local embeddings (all-MiniLM-L6-v2) -- matches MEANING.

## Headline: the shipped system against the keyword baseline

The same main-set questions (20 scored + 3 out-of-scope, fixed before anything ran) through `shipped` (exactly what the app runs) and `tfidf_k5` (keyword search over the same chunks, non-AI retrieval). A no-retrieval model is NOT the baseline: it has never seen these fictional documents, so it scores near zero and teaches nothing.

| measure | what it asks | shipped | keyword baseline | difference |
|---|---|---|---|---|
| **answer correctness** | every key fact present (code check, eval_key_facts.json) | 80% | 75% | +5 pts |
| correctness, cross-division only | the questions this project exists for | 64% | 55% | +9 pts |
| **faithfulness** | every claim supported by the notes (judge; target 85%) | 89% (n=18) | 100% (n=19) | -11 pts |
| declined | said 'The documents do not say', or handed to a person | 22% | 17% | +4 pts |
| declines that were right | out of scope, or the needed documents were not retrieved | 80% (n=5) | 100% (n=4) | |
| **silent failures** | answered although the needed documents were NOT retrieved | 3 (1 of them wrong) | 3 (3 wrong) | |
| out-of-scope declined | the 3 questions the corpus cannot answer | 100% | 100% | |
| figures found in cited docs | every number, date and id is in a cited document | 94% | 100% | |
| handed to a person | retrieval score below 0.45, no model call | 9% | 0% | |

Why both correctness and faithfulness: faithfulness alone is won by quoting a chunk back, and correctness alone cannot tell a grounded answer from a lucky one. The two abstention rows are the numbers the brief asks for: how often it declines, and whether the declines were the questions it would have got wrong.

## Every configuration, main set

| system | answer correctness | cross-division | faithfulness (judge) | declined | declines right | silent failures | OOS declined | citation valid | figures supported | handed to person | tokens in/out |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `shipped` (what the app ships) | 80% | 64% | 89% (n=18) | 22% | 80% | 3 | 100% | 83% | 94% | 9% | 1387 / 53 |
| `tfidf_k5` (THE baseline) | 75% | 55% | 100% (n=19) | 17% | 100% | 3 | 100% | 89% | 100% | 0% | 1585 / 55 |

## By question set

The main set was written before the system ran; the others were added later, so read them separately. The independent set was written by a different model from the documents alone.

| set | system | scored questions | answer correctness | OOS declined | declined |
|---|---|---|---|---|---|
| main | `shipped` | 20 | 80% | 100% | 22% |
| main | `tfidf_k5` | 20 | 75% | 100% | 17% |
| extra | `shipped` | 2 | 100% | n/a | 0% |
| extra | `tfidf_k5` | 2 | 50% | n/a | 50% |
| breaker | `shipped` | 4 | 75% | 100% | 33% |
| breaker | `tfidf_k5` | 4 | 75% | 100% | 33% |
| partial | `shipped` | 6 | 67% | n/a | 0% |
| partial | `tfidf_k5` | 6 | 83% | n/a | 0% |
| independent | `shipped` | 5 | 100% | 100% | 17% |
| independent | `tfidf_k5` | 5 | 100% | 100% | 17% |

## Partially answerable questions

Each asks for one thing the documents answer and one they do not (checked absent from all 18 documents by `self_test.py`). The right behaviour: answer the first part, say the second is not in the documents, invent nothing. Declining outright loses the part it could answer; supplying the missing part is the silent failure.

| system | answerable part correct | says the rest is missing | declined outright | faithful (judge) |
|---|---|---|---|---|
| `shipped` | 67% | 67% | 0% | 100% (n=6) |
| `tfidf_k5` | 83% | 67% | 0% | 100% (n=6) |

## `shipped`: scored questions that failed the correctness check (7)

- **CD3** (needed docs NOT retrieved): missing [['48', 'two days', '2 days'], ['30%', '30 %', '30 percent']]; answer: 'The documents do not say.  \nCited:'
- **CD9** (needed docs retrieved): missing [['45000', '45,000'], ['tool steel', 'ms-07']]; answer: 'The documents do not say. [Low retrieval confidence: the best match scored 0.37, below 0.45, so this question is passed to a human reviewer instead of being answered.]'
- **CD11** (needed docs retrieved): missing [['850', '5%', '5 %', 'handling']]; answer: 'The stamping die for a custom jewellery order is manufactured by the CNC division, as indicated by the notes. The machining cost for the stamping die is billed as a one-time tooling charge, sourced from a CNC division wo'
- **CD12** (needed docs NOT retrieved): missing [['0470'], ['stamping die', 'die']]; answer: 'CNC is currently machining a buffer inventory of MS-07 tool steel for the Jewellery division to support expedited internal work orders. \n\nCited: jwl-01'
- **VM1** (needed docs retrieved): missing [['180000', '180,000']]; answer: "The extra filling-line equipment was funded through an intercompany working-capital facility extended by the Jewellery division rather than external financing, as per the Group's Q2 treasury decision. Cited: fnb-06"
- **PA1** (needed docs retrieved): missing [['4 business days', 'four business days', '4 days', 'four days']]; answer: 'The external CNC order that was delayed to make room for the Aurora rush order is Order #C-4471, which was placed by a non-TGMOK client for precision bracket components. \n\nCited: cnc-02, cnc-06'
- **PA4** (needed docs NOT retrieved): missing [['2026-07-10', '10 july', 'july 10', '10 jul'], ['in progress', 'not yet', 'still', 'underway', 'not delivered']]; answer: 'The custom stamping die for the Jewellery division is part of the quote issued on 2026-06-25, but the notes do not specify a due date for its delivery. Therefore, I cannot confirm if it was delivered on time based on the'

Judge marked 2 answers unfaithful:

- **CD1**: The citation 'cnc-05' is not present in the provided NOTES.
- **S4**: The required tolerance for work order CNC-WO-0442 was ±0.02mm

## `tfidf_k5`: scored questions that failed the correctness check (8)

- **CD3** (needed docs NOT retrieved): missing [['48', 'two days', '2 days'], ['30%', '30 %', '30 percent']]; answer: 'The documents do not say.  \nCited:'
- **CD8** (needed docs NOT retrieved): missing [['250000', '250,000', 'cfo']]; answer: 'F&B funded its second capping head (FL2-CAP-02) through an intercompany working-capital facility extended by the Jewellery division rather than external financing. The facility amount was $180,000, drawn in full, with re'
- **CD9** (needed docs retrieved): missing [['45000', '45,000']]; answer: "CNC's raw-material buffer is supported by an intercompany financing facility extended by the Jewellery division, specifically for a buffer inventory of MS-07 tool steel to support expedited internal work orders. \n\nCited:"
- **CD11** (needed docs NOT retrieved): missing [['850', '5%', '5 %', 'handling']]; answer: 'The stamping die for a custom jewellery order is manufactured by the CNC division, as indicated in the notes. The machining cost for the custom stamping die is billed as a one-time tooling charge, sourced from a CNC divi'
- **CD12** (needed docs NOT retrieved): missing [['0470']]; answer: 'CNC is currently machining a custom stamping die for the Jewellery division, which is due by 2026-07-10. \n\nCited: cnc-06'
- **NM2** (needed docs NOT retrieved): missing [['intercompany', 'jewellery']]; answer: 'The documents do not say.  \nCited: 3'
- **VM1** (needed docs retrieved): missing [['180000', '180,000']]; answer: 'The second capping head installed in June 2026 was funded through an intercompany working-capital facility extended by the Jewellery division rather than external financing. Cited: fnb-06'
- **PA1** (needed docs retrieved): missing [['4 business days', 'four business days', '4 days', 'four days']]; answer: 'The external CNC order that was delayed to make room for the Aurora rush order is Order #C-4471, placed by a non-TGMOK client for precision bracket components. Cited: cnc-02, cnc-04'

Judge marked 0 answers unfaithful:


