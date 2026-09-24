# Code map

Flat, single-purpose Python modules at the repository root; no packages. `data/` holds
everything about the data (the corpus, the prompts that generated it, the answer key, the
question sets and the checker that validates them), `docs/` describes the instruments, and
`results/` holds every number the write-up quotes. Settings live in one file, `config.py`.

| file | lines | what it does |
|---|---|---|
| `config.py` | 95 | The only place to change a setting: models, chunking, top-k, titled embedding, the hand-off threshold, the token cap, prices, cost-model assumptions, and the corpus manifest (`DOC_ID_TO_PATH`). Standard library only. |
| `rag_core.py` | 345 | The pipeline, shared by the app, the evaluation and the demo: load corpus -> chunk -> `build_index` (embed) -> `retrieve` -> `answer_question`; `classify_document` -> `format_upload_content` -> `generate_impact_snapshot` for uploads. The prompts (`GROUNDED`, `CLASSIFY_SYSTEM`, `IMPACT_SYSTEM`) are here. |
| `guardrails.py` | 140 | Every Section 8 mitigation that is code, not prompt: token cap, injection scan, confidence hand-off, exact abstention, the figure check, the malformed-citation check. No model calls. |
| `app.py` | 340 | Streamlit interface: upload -> injection scan -> classify -> a person confirms -> impact brief -> chat. The only code that writes (to `data/uploads/`). |
| `doc_parser.py` | 30 | PDF/DOCX/TXT to text. No model calls. |
| `harness.py` | 600 | The evaluation: question sets, 9 retrieval configs (`shipped` and the `tfidf_k5` baseline first), code checks, the judge call, aggregation (correctness, faithfulness, the two abstention numbers, silent failures), the judge's precision/recall against hand labels, the leakage check. |
| `run_eval.py` | 430 | The entry point a marker runs: `--retrieval-only`, `--chunk-sweep`, `--leakage`, `--dry-run`, `--run`, `--agreement`. |
| `run_guardrails.py` | 150 | Section 8 checklist: 28 named cases against every guardrail -> `results/guardrails.md`. Exits non-zero on a failure. |
| `self_test.py` | 110 | Checks the instruments, not the system: every key fact appears in its source documents, the checkers reject wrong answers and abstentions. |
| `cost_model.py` | 250 | Calls x tokens x price, plus the cost of a person redoing a wrong answer. `--estimate` (free, the real prompts, time-to-deploy) -> `results/cost_estimate.md`; after a live run -> `results/cost_model.md`. |
| `demo_citation_fix.py` | 120 | The failure found in the screen recordings (fake citations), re-run live -> `results/citation_fix.md`. |
| `make_docs.py` | 100 | Regenerates `docs/EVALUATION_SET.md` and `docs/BLIND_QUESTION_PACK.md` from the question files. |
| `data/check_my_data.py` | 120 | Corpus, manifest, answer key and key facts hang together. Run after every data change. |
| `Tanya_RAG_Notebook.ipynb` | | The smallest first version, and the evaluation told as a narrative, on the same `config.py` settings. |

## Suggested reading order

1. `config.py` -- every decision that has a number, with the measurement behind it.
2. `rag_core.py` -- the whole pipeline in one file; `answer_question` is ten lines.
3. `guardrails.py` -- what stops a confident wrong answer, and what does not.
4. `harness.py`: `CONFIGS`, `run_rag_question` and `aggregate` -- how each setup is scored.
5. `results/retrieval_recall.md`, `results/guardrails.md`, `results/cost_estimate.md`, then
   `results/summary.md` after a live run.

## The shape of one question

```
question
  -> embed (title-prefixed chunks, all-MiniLM-L6-v2, local)  -> top-5 chunks, each tagged with document id + division
  -> best score below 0.45?  yes: "The documents do not say." + hand to a person, NO model call
  -> session token cap reached?  yes: stop loudly
  -> GROUNDED prompt: answer ONLY from the numbered notes, cite the real ids, or say "The documents do not say."
  -> answer
  -> figure check: every number, date and id in the answer appears in a cited document (warn if not)
evaluation only:
  -> correctness (key facts, code) · citation validity (code) · faithfulness (judge, a different model family)
  -> declined? right or wrong (was the evidence retrieved?) · answered without the evidence? (silent failure)
```

## Module boundaries

- **Settings flow one way:** `config.py` -> everything else. Nothing redefines a setting locally,
  so the app, the notebook and the evaluation cannot drift apart (two earlier drifts, a duplicated
  prompt and a duplicated chunk size, are why).
- **Uploads cannot move a reported number.** The app writes only to `data/uploads/`; git ignores
  it and the evaluation reads only the fixed corpus in `data/fnb`, `data/cnc`, `data/jewellery`.
- **One index recipe.** The app and the demo build their index through `rag_core.build_index`;
  the evaluation's `shipped` config uses the same chunking, titling and top-k from `config.py`.
- **One id scheme.** Documents are `fnb-01` ... `jwl-06` in the app, the answer key, the notebook
  and every results file; uploads are `upload-<division>-<file>`.
- **The key is read in one place per entry point** (`run_eval.load_key`, the app's sidebar) and
  never written to disk.

## Commands

| purpose | command | key? |
|---|---|---|
| data hangs together | `python data/check_my_data.py` | no |
| the instruments are sound | `python self_test.py` | no |
| guardrail checklist | `python run_guardrails.py` | no |
| retrieval recall, 9 configs, every miss diagnosed | `python run_eval.py --retrieval-only` | no |
| why 200-word chunks | `python run_eval.py --chunk-sweep` | no |
| does a question contain its own answer? | `python run_eval.py --leakage` | no |
| cost per query and time to deploy, estimated | `python cost_model.py --estimate` | no |
| the whole live path with a fake model | `python run_eval.py --dry-run --yes` | no |
| the app (retrieval works without a key) | `streamlit run app.py` | for answers |
| **the answer-level evaluation** (about $0.62) | `python run_eval.py --run` | yes |
| the judge against your hand labels | `python run_eval.py --agreement` | no |
| measured cost per successful answer | `python cost_model.py` | no (after `--run`) |
| the recorded citation bug, re-run | `python demo_citation_fix.py` | yes |

## Current results

| | shipped (what the app runs) | keyword baseline | source |
|---|---|---|---|
| **answer correctness**, same 20 questions | 80% | 75% | `results/notebook_run.md` |
| **faithfulness** (target 85%), same 20 questions | 80% | 95% | same |
| declines that were right | 4 of 4 | | same |
| silent failures (answered without the needed documents) | 3, 1 of them wrong | | same |
| cross-division recall (a chunk from every division needed) | 100% | 91% | `results/retrieval_recall.md` |
| document recall (every document needed) | 88% | 91% | same |
| words of notes sent per question | 837 | 865 | same |
| unanswerable questions caught by the 0.45 threshold | 2 of 6 (and 1 of 31 answerable wrongly handed off) | n/a | same, abstention table |
| guardrail cases behaving as designed | 28 of 28 | | `results/guardrails.md` |
| model cost per question (estimated) | about $0.0003 | about $0.0003 | `results/cost_estimate.md` |

The answer rows come from the final notebook run, which uses the app's retrieval and prompt but not its
0.45 hand-off; `python run_eval.py --run` adds the hand-off, every other configuration and the judge's
hand-checked precision and recall.
