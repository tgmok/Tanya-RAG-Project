# Answer-level results: the notebook run of 2026-09-24

Copied **verbatim** from the saved outputs of `Tanya_RAG_Notebook.ipynb` (sections 6, 7, 8 and 10); nothing here is recomputed. The notebook runs the app's retrieval and prompt (settings from `config.py`: 200-word chunks, overlap 50, top-5, title-prefixed embedding, generation `openai/gpt-4o-mini`) **without** the app's confidence hand-off below 0.45, and judges faithfulness with `google/gemini-2.5-flash`. 20 scored + 3 out-of-scope questions from the main set, fixed before anything ran. One judge pass per answer; the judge has not yet been checked against hand labels (`python run_eval.py --run`, then `--agreement`).

## Headline

| | embeddings (what the app runs) | keyword baseline (TF-IDF, same chunks) | target |
|---|---|---|---|
| answer correctness (every key fact present, code check) | 80% | 75% | |
| faithfulness (every claim supported by the notes, judge) | 80% | 95% | 85% |
| context recall, cross-division (every division covered) | 100% | 91% (`results/retrieval_recall.md`) | 80% |
| out-of-scope questions declined | 3 of 3 | | |
| declines that were right (out of scope, or evidence not retrieved) | 4 of 4 | | |
| silent failures (answered without the needed documents) | 3, 1 of them wrong | | |

Reading it: embeddings get one more question right than keyword search, but three more answers judged unfaithful, so on this run the system **misses the 85% faithfulness target** and the non-AI baseline is the more faithful of the two. On 20 questions one answer is 5 points, and two of the four embedding answers judged unfaithful (CD1, S4) were also judged correct, which the unmeasured judge may be over-strict about.

## Section 6 · L1 context recall (cell 18)

```
CD1    cross_division   division_recall=OK   doc_overlap=50%
CD2    cross_division   division_recall=OK   doc_overlap=50%
CD3    cross_division   division_recall=OK   doc_overlap=67%
CD4    cross_division   division_recall=OK   doc_overlap=100%
CD5    cross_division   division_recall=OK   doc_overlap=100%
CD6    cross_division   division_recall=OK   doc_overlap=100%
CD7    cross_division   division_recall=OK   doc_overlap=100%
CD8    cross_division   division_recall=OK   doc_overlap=100%
CD9    cross_division   division_recall=OK   doc_overlap=100%
S9     single_division  division_recall=OK   doc_overlap=100%
CD11   cross_division   division_recall=OK   doc_overlap=100%
CD12   cross_division   division_recall=OK   doc_overlap=0%
S1     single_division  division_recall=OK   doc_overlap=100%
S2     single_division  division_recall=OK   doc_overlap=100%
S3     single_division  division_recall=OK   doc_overlap=100%
S4     single_division  division_recall=OK   doc_overlap=100%
S5     single_division  division_recall=OK   doc_overlap=100%
S6     single_division  division_recall=OK   doc_overlap=100%
S7     single_division  division_recall=OK   doc_overlap=100%
S8     single_division  division_recall=OK   doc_overlap=100%

context recall on cross-division cases: 100%  (target >=80%, Section 7)
context recall overall: 100%
```

## Section 7 · L2 answer correctness, faithfulness, abstention (cell 20)

```
CD1    faithful=False correct=True  evidence=False ok
CD2    faithful=True  correct=True  evidence=False ok
CD3    faithful=True  correct=False evidence=False DECLINED
CD4    faithful=True  correct=False evidence=True  MISSING [['reallocat', 'reprioritis', 'rush order', 'capping']]
CD5    faithful=True  correct=True  evidence=True  ok
CD6    faithful=True  correct=True  evidence=True  ok
CD7    faithful=True  correct=True  evidence=True  ok
CD8    faithful=True  correct=True  evidence=True  ok
CD9    faithful=True  correct=True  evidence=True  ok
S9     faithful=True  correct=True  evidence=True  ok
CD11   faithful=False correct=False evidence=True  MISSING [['850', '5%', '5 %', 'handling']]
CD12   faithful=False correct=False evidence=False MISSING [['0470'], ['stamping die', 'die']]
S1     faithful=True  correct=True  evidence=True  ok
S2     faithful=True  correct=True  evidence=True  ok
S3     faithful=True  correct=True  evidence=True  ok
S4     faithful=False correct=True  evidence=True  ok
S5     faithful=True  correct=True  evidence=True  ok
S6     faithful=True  correct=True  evidence=True  ok
S7     faithful=True  correct=True  evidence=True  ok
S8     faithful=True  correct=True  evidence=True  ok
OOS-FNB  declined=True   The documents do not say.  
Cited:
OOS-CNC  declined=True   The documents do not say.  
Cited:
OOS-JWL  declined=True   The documents do not say.  
Cited:

answer correctness: 80%  (key facts present -- the check faithfulness cannot fake)
faithfulness:       80%  (target >=85%, Section 7)
out-of-scope declined: 100%

Abstention, the two numbers (Section 7):
  how often it declines:             4/23 questions
  declines that were right:          4/4  (out of scope, or the evidence was not retrieved)
Silent failures (Section 8): answered without the needed documents on 3 question(s), 1 of them wrong: ['CD1', 'CD2', 'CD12']
```

## Section 8 · the keyword baseline on the same 20 questions (cell 22)

```
CD1    (keyword) faithful=True  correct=True  The packaging change that forced F&B to order new CNC tooling was a ch
CD2    (keyword) faithful=False correct=True  Yes, the CNC tooling for the Aurora packaging change was installed imm
CD3    (keyword) faithful=True  correct=False The documents do not say.  
Cited:
CD4    (keyword) faithful=True  correct=True  External CNC client order C-4471 was delayed by 4 days to accommodate 
CD5    (keyword) faithful=True  correct=True  The second capping head (FL2-CAP-02) was installed ahead of the Aurora
CD6    (keyword) faithful=True  correct=True  The specific external CNC order that was pushed back due to the F&B ru
CD7    (keyword) faithful=True  correct=True  CNC Production Planning recommended that F&B Client Services flag rush
CD8    (keyword) faithful=True  correct=False F&B funded its second capping head (FL2-CAP-02) through an intercompan
CD9    (keyword) faithful=True  correct=False CNC's raw-material buffer is supported by an intercompany working-capi
S9     (keyword) faithful=True  correct=True  A piece failing certification is quarantined and routed back to Produc
CD11   (keyword) faithful=True  correct=False The stamping die for a custom jewellery order is manufactured by the C
CD12   (keyword) faithful=True  correct=False CNC is currently machining a custom stamping die for the Jewellery div
S1     (keyword) faithful=True  correct=True  If a hygiene non-conformance is found, it halts the affected line unti
S2     (keyword) faithful=True  correct=True  The concentration risk flagged by Group Treasury in the F&B Q3 financi
S3     (keyword) faithful=True  correct=True  No, an urgent internal tooling request does not waive CNC's lockout-ta
S4     (keyword) faithful=True  correct=True  The required tolerance for work order CNC-WO-0442 was ±0.02mm, and an 
S5     (keyword) faithful=True  correct=True  A Jewellery division client quote is valid for 5 business days from is
S6     (keyword) faithful=True  correct=True  The custody control for accessing raw gold stock in the vault requires
S7     (keyword) faithful=True  correct=True  A custom jewellery piece is not eligible for return, as stated in the 
S8     (keyword) faithful=True  correct=True  The six checks that must pass before an F&B pilot run is cleared for f

measure               embeddings (Sec 7)  keyword baseline
answer correctness                   80%               75%
faithfulness                         80%               95%
```

## Section 10 · smallest first version (cell 28)

```
Q: What packaging spec changes require new CNC tooling?
A: Any change to cap diameter, thread pitch, or bottle neck finish requires new tooling from the CNC division. The existing filling-line tooling cannot be re-machined on-site and must be replaced via a CNC work order. Cited: fnb-01

Code check: WORKED: every figure is in the cited document

Hand check -- does the cited chunk contain what the answer says?
  [1] (fnb-01) # SOP-FNB-014 — Packaging Specification Change Procedure **Division:** F&B Contract Manufacturing (TGMOK Holdings) **Effective:** 2026-06-01 · **Owner:** Packaging Engineering, F&B ## Purpose Governs how a client-requested change to bottle, cap, or carton specification is evaluated, approved, and rolled out on the production line. ## Procedure 1. Client Services logs the requested change in the Packaging Change Register within 1 business day of receipt. 2. Packaging Engineering assesses whether the change is compatible with existing filling and capping tooling. **Any change to cap diameter, thread pitch, or bottle neck finish requires new tooling from the CNC division** — the existing filling-line tooling cannot be re-machined on-site and must be replaced via a CNC work order. 3. If new tooling is required, Packaging Engineering raises a CNC Tooling Request (form CNC-TR-01) and the change is held at "pending tooling" status until CNC confirms a delivery date. 4. Once tooling is confirmed, a pilot run of 500 units is completed and inspected against QC-FNB-002 before full-line rollout. 5. Client sign-off is required before the new packaging appears on any shipped order. ## Recent example Client Aurora Beverages (contract AB-2231) requested a narrower bottle neck for their sparkling line in May 2026 to reduce
  [2] (fnb-01) pilot run of 500 units is completed and inspected against QC-FNB-002 before full-line rollout. 5. Client sign-off is required before the new packaging appears on any shipped order. ## Recent example Client Aurora Beverages (contract AB-2231) requested a narrower bottle neck for their sparkling line in May 2026 to reduce material cost. Cap diameter changed from 28mm to 26mm, which changed the thread pitch — this triggered a CNC Tooling Request (CNC-TR-01, logged 2026-05-14) since the existing capping head could not accommodate the new thread without replacement tooling. ## Escalation A packaging change that is not accompanied by a CNC Tooling Request when required must not proceed to pilot run. Any line supervisor may halt a pilot run pending confirmation.
```

## Session (cell 30)

```
tokens this session: 137684 in / 2676 out
embedding backend: local embeddings (all-MiniLM-L6-v2) — matches MEANING
chunking: CHUNK_WORDS=200, OVERLAP=50, TOP_K=5
```
