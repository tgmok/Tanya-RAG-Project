# Answer-level evaluation

Generation `openai/gpt-4o-mini`; judge `google/gemini-2.5-flash` (a different model family from the generator). Run 2026-09-29. Embedder: local embeddings (all-MiniLM-L6-v2) -- matches MEANING.

## Headline: the shipped system against the keyword baseline

The same main-set questions (20 scored + 3 out-of-scope, fixed before anything ran) through `shipped` (exactly what the app runs) and `tfidf_k5` (keyword search over the same chunks, non-AI retrieval). A no-retrieval model is NOT the baseline: it has never seen these fictional documents, so it scores near zero and teaches nothing.

| measure | what it asks | shipped | keyword baseline | difference |
|---|---|---|---|---|
| **answer correctness** | every key fact present (code check, eval_key_facts.json) | 85% | 75% | +10 pts |
| correctness, cross-division only | the questions this project exists for | 73% | 55% | +18 pts |
| **faithfulness** | every claim supported by the notes (judge; target 85%) | 84% (n=19) | 100% (n=20) | -16 pts |
| declined | said 'The documents do not say', or handed to a person | 17% | 13% | +4 pts |
| declines that were right | out of scope, or the needed documents were not retrieved | 75% (n=4) | 100% (n=3) | |
| **silent failures** | answered although the needed documents were NOT retrieved | 1 (1 of them wrong) | 4 (4 wrong) | |
| out-of-scope declined | the 3 questions the corpus cannot answer | 100% | 100% | |
| figures found in cited docs | every number, date and id is in a cited document | 89% | 100% | |
| handed to a person | retrieval score below 0.45, no model call | 9% | 0% | |

Why both correctness and faithfulness: faithfulness alone is won by quoting a chunk back, and correctness alone cannot tell a grounded answer from a lucky one. The two abstention rows are the numbers the brief asks for: how often it declines, and whether the declines were the questions it would have got wrong.

## Before and after reference-following

The same run and the same questions through `previous_shipped` (the retrieval before) and `shipped` (with reference-following). Adopted only if the answers improve, not only the retrieval.

| measure | before | after | change |
|---|---|---|---|
| answer correctness | 80% | 85% | +5 pts |
| correctness, cross-division only | 64% | 73% | +9 pts |
| faithfulness (judge) | 89% (n=18) | 84% (n=19) | -5 pts |
| silent failures | 3 (1 wrong) | 1 (1 wrong) | |
| input tokens per question | 1387 | 1904 | |

## Every configuration, main set

| system | answer correctness | cross-division | faithfulness (judge) | declined | declines right | silent failures | OOS declined | citation valid | figures supported | handed to person | tokens in/out |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `shipped` (what the app ships) | 85% | 73% | 84% (n=19) | 17% | 75% | 1 | 100% | 79% | 89% | 9% | 1904 / 53 |
| `previous_shipped` (before reference-following) | 80% | 64% | 89% (n=18) | 22% | 80% | 3 | 100% | 89% | 94% | 9% | 1387 / 55 |
| `tfidf_k5` (THE baseline) | 75% | 55% | 100% (n=20) | 13% | 100% | 4 | 100% | 90% | 100% | 0% | 1585 / 58 |

## By question set

The main set was written before the system ran; the others were added later, so read them separately. The independent set was written by a different model from the documents alone.

| set | system | scored questions | answer correctness | OOS declined | declined |
|---|---|---|---|---|---|
| main | `shipped` | 20 | 85% | 100% | 17% |
| main | `previous_shipped` | 20 | 80% | 100% | 22% |
| main | `tfidf_k5` | 20 | 75% | 100% | 13% |
| extra | `shipped` | 2 | 100% | n/a | 0% |
| extra | `previous_shipped` | 2 | 100% | n/a | 0% |
| extra | `tfidf_k5` | 2 | 100% | n/a | 0% |
| breaker | `shipped` | 4 | 75% | 50% | 17% |
| breaker | `previous_shipped` | 4 | 75% | 100% | 33% |
| breaker | `tfidf_k5` | 4 | 75% | 100% | 33% |
| partial | `shipped` | 6 | 83% | n/a | 0% |
| partial | `previous_shipped` | 6 | 67% | n/a | 0% |
| partial | `tfidf_k5` | 6 | 83% | n/a | 0% |
| independent | `shipped` | 5 | 100% | 100% | 17% |
| independent | `previous_shipped` | 5 | 100% | 100% | 17% |
| independent | `tfidf_k5` | 5 | 100% | 100% | 17% |

## Partially answerable questions

Each asks for one thing the documents answer and one they do not (checked absent from all 18 documents by `self_test.py`). The right behaviour: answer the first part, say the second is not in the documents, invent nothing. Declining outright loses the part it could answer; supplying the missing part is the silent failure.

| system | answerable part correct | says the rest is missing | declined outright | faithful (judge) |
|---|---|---|---|---|
| `shipped` | 83% | 67% | 0% | 100% (n=6) |
| `previous_shipped` | 67% | 50% | 0% | 67% (n=6) |
| `tfidf_k5` | 83% | 83% | 0% | 100% (n=6) |

## `shipped`: scored questions that failed the correctness check (5)

- **CD9** (needed docs retrieved): missing [['45000', '45,000'], ['tool steel', 'ms-07']]; answer: 'The documents do not say. [Low retrieval confidence: the best match scored 0.37, below 0.45, so this question is passed to a human reviewer instead of being answered.]'
- **CD11** (needed docs retrieved): missing [['850', '5%', '5 %', 'handling']]; answer: 'The stamping die for a custom jewellery order is manufactured by the CNC division. The machining cost for the custom stamping die is billed as a one-time tooling charge, sourced from a CNC division work order, and is dis'
- **CD12** (needed docs NOT retrieved): missing [['0470']]; answer: 'CNC is currently machining a custom stamping die for the Jewellery division, which is due on 2026-07-10. \n\nCited: cnc-07'
- **VM1** (needed docs retrieved): missing [['180000', '180,000']]; answer: 'The second capping head installed in June 2026 was funded through an intercompany working-capital facility extended by the Jewellery division rather than external financing. Cited: fnb-06'
- **PA1** (needed docs retrieved): missing [['4 business days', 'four business days', '4 days', 'four days']]; answer: 'The external CNC order that was delayed to make room for the Aurora rush order is Order #C-4471, which was placed by a non-TGMOK client for precision bracket components. \n\nCited: cnc-02, cnc-06'

Judge marked 3 answers unfaithful:

- **CD2**: fnb-03
- **CD11**: jwl-03
- **S4**: The notes do not contain a document cnc-04.

## `previous_shipped`: scored questions that failed the correctness check (7)

- **CD3** (needed docs NOT retrieved): missing [['48', 'two days', '2 days'], ['30%', '30 %', '30 percent']]; answer: 'The notes do not provide specific information about the duration from packaging-change request to tooling delivery or any applicable surcharge for that expedite. \n\nCited: The documents do not say.'
- **CD9** (needed docs retrieved): missing [['45000', '45,000'], ['tool steel', 'ms-07']]; answer: 'The documents do not say. [Low retrieval confidence: the best match scored 0.37, below 0.45, so this question is passed to a human reviewer instead of being answered.]'
- **CD11** (needed docs retrieved): missing [['850', '5%', '5 %', 'handling']]; answer: 'The stamping die for a custom jewellery order is manufactured by the CNC division, as indicated in the notes. The machining cost for the custom stamping die is billed as a one-time tooling charge, sourced from a CNC divi'
- **CD12** (needed docs NOT retrieved): missing [['0470'], ['stamping die', 'die']]; answer: 'CNC is currently machining a buffer inventory of MS-07 tool steel for the Jewellery division to support expedited internal work orders. \n\nCited: jwl-01'
- **VM1** (needed docs retrieved): missing [['180000', '180,000']]; answer: "The extra filling-line equipment was funded through an intercompany working-capital facility extended by the Jewellery division rather than external financing, as per the Group's Q2 treasury decision. Cited: fnb-06"
- **PA1** (needed docs retrieved): missing [['4 business days', 'four business days', '4 days', 'four days']]; answer: 'The external CNC order that was delayed to make room for the Aurora rush order is Order #C-4471, which was placed by a non-TGMOK client for precision bracket components. \n\nCited: cnc-02, cnc-06'
- **PA4** (needed docs NOT retrieved): missing [['2026-07-10', '10 july', 'july 10', '10 jul'], ['in progress', 'not yet', 'still', 'underway', 'not delivered']]; answer: 'The custom stamping die for the Jewellery division is part of the quote issued on 2026-06-25, and the total quote is valid for 5 business days from that date, which means it would need to be accepted by 2026-06-30. Howev'

Judge marked 4 answers unfaithful:

- **CD1**: The citation 'cnc-05' is not present in the provided NOTES.
- **S4**: The required tolerance for work order CNC-WO-0442 was ±0.02mm
- **PA4**: The answer states that the custom stamping die is part of the quote issued on 2026-06-25, and that the quote is valid for 5 business days from that date, which means it would need to be accepted by 2026-06-30.
- **PA6**: The machining was performed by CNC Mill 3, which is operated by Equipment Maintenance, CNC.

## `tfidf_k5`: scored questions that failed the correctness check (7)

- **CD3** (needed docs NOT retrieved): missing [['30%', '30 %', '30 percent']]; answer: 'The packaging-change request for Aurora Beverages was logged on 2026-05-14, and the new capping-head tooling was delivered on 2026-05-16. This indicates that it took 2 days from the request to tooling delivery. The notes'
- **CD8** (needed docs NOT retrieved): missing [['250000', '250,000', 'cfo']]; answer: 'F&B funded its second capping head (FL2-CAP-02) through an intercompany working-capital facility extended by the Jewellery division rather than external financing. The facility amount was $180,000, drawn in full, with re'
- **CD9** (needed docs retrieved): missing [['45000', '45,000']]; answer: "CNC's raw-material buffer is supported by an intercompany financing facility extended by the Jewellery division, specifically for a buffer inventory of MS-07 tool steel to support expedited internal work orders. \n\nCited:"
- **CD11** (needed docs NOT retrieved): missing [['850', '5%', '5 %', 'handling']]; answer: 'The stamping die for a custom jewellery order is manufactured by the CNC division, and the machining cost is billed as a one-time tooling charge sourced from a CNC division work order rather than an external toolmaker, p'
- **CD12** (needed docs NOT retrieved): missing [['0470']]; answer: 'CNC is currently machining a custom stamping die for the Jewellery division, which is due by 2026-07-10. \n\nCited: cnc-06'
- **VM1** (needed docs retrieved): missing [['180000', '180,000']]; answer: 'The second capping head installed in June 2026 was funded through an intercompany working-capital facility extended by the Jewellery division rather than external financing. Cited: fnb-06'
- **PA1** (needed docs retrieved): missing [['4 business days', 'four business days', '4 days', 'four days']]; answer: 'The external CNC order that was delayed to make room for the Aurora rush order is Order #C-4471, which was placed by a non-TGMOK client for precision bracket components. Cited: cnc-02, cnc-04'

Judge marked 0 answers unfaithful:


