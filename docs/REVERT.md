# Reverting the Streamlit UI

Everything the UI added is additive and self-contained. Nothing it did touched
`Tanya_RAG_Notebook.ipynb`, `eval_questions.json`, `data_dictionary.json`,
`check_my_data.py`, or any file under `data/fnb/`, `data/cnc/`, or
`data/jewellery/`. To go back to exactly the state before the UI existed, just
tell me to revert, or delete these yourself:

```
webapp/                  the entire Streamlit app (app.py, rag_core.py, doc_parser.py,
                          requirements.txt)
data/uploads/             any documents uploaded through the app during testing
docs/SYSTEM_FLOW.md       the architecture/flowchart doc written for the UI
docs/REVERT.md            this file
../.claude/launch.json    the dev-server config used to preview the app during
                          development (one level up, in A1_individual/.claude/)
```

Nothing else needs to change. `check_my_data.py` skips `data/uploads/` and
`data/validation_real/` (see `NON_CORPUS_DIRS`), so its validation of the fixed corpus is
unaffected whether or not uploads exist. (An earlier version of this file said the validator
never looked at those folders. It did, and flagged them; fixed on 2026-09-21.)

## What was never touched

- `Tanya_RAG_Notebook.ipynb` -- unchanged
- `eval_questions.json` -- unchanged, still the same 23 hand-verified questions
- `data_dictionary.json`, `generation_prompts.md` -- unchanged
- `check_my_data.py` -- edited on 2026-09-21 (skips `uploads`/`validation_real`; also checks
  `eval_key_facts.json`). Those edits belong to the evaluation work below, not the UI.

## Evaluation harness (added 2026-09-21, separate from the UI)

To remove it: delete `eval/`, `eval_key_facts.json`, `results/`, `docs/JUDGE_PROMPT.md`,
`docs/EVALUATION_SET.md`, `docs/BLIND_QUESTION_PACK.md`, `docs/GOOD_RUN.md`, the "Evaluation"
section at the end of `README.md`, and block 6 in `check_my_data.py`. The corpus, the answer key
(`eval_questions.json`) and the notebook were not modified by it.
- `data/fnb/`, `data/cnc/`, `data/jewellery/` -- unchanged
- `data/validation_real/` -- unchanged

## Quick command to remove everything the UI added

```bash
rm -rf webapp data/uploads docs/SYSTEM_FLOW.md docs/REVERT.md
```

Run that from the `tanya-rag-project` root, or just ask me to do it and I will.
