# Code map

| file | what it does |
|---|---|
| `webapp/rag_core.py` | shared by the app and the evaluation: corpus loading, chunking, embeddings, retrieval, grounded answering, upload classification, impact snapshot, the citation-content check and the confidence hand-off |
| `webapp/app.py` | Streamlit interface: upload, classify, confirm, snapshot, chat |
| `webapp/doc_parser.py` | PDF and DOCX to text. No model calls. |
| `eval/harness.py` | question sets, retrieval configurations, code checks, judge call, aggregation, spot-check |
| `eval/run_eval.py` | the entry point: retrieval report, chunk sweep, leakage check, live run, agreement |
| `eval/cost_model.py` | three-layer cost per successful answer, from measured tokens and pass rates |
| `eval/self_test.py` | checks the instruments: key facts against the documents, the checkers, the citation and classifier logic |
| `eval/make_docs.py` | regenerates `docs/EVALUATION_SET.md` and the blind-question pack |
| `check_my_data.py` | corpus, answer key and key facts hang together |
| `eval_questions.json`, `eval_key_facts.json` | the designed questions and their code-checkable facts |
| `eval/extra_questions.json`, `breaker_questions.json`, `independent_questions.json` | near-miss, break-it and independent sets |

## Suggested reading order

1. `docs/ALIGNMENT.md` (what was promised and what was built)
2. `webapp/rag_core.py` (the whole pipeline in one file)
3. `eval/harness.py`, `retrieve_config` and `run_rag_question` (how each setup is scored)
4. `results/retrieval_recall.md`, `results/chunk_sweep.md`, `results/leakage.md`, then
   `results/summary.md` after a live run

## One run

question -> embed -> top-k chunks (each labelled with its document and division) -> grounded prompt
("answer ONLY from the notes, cite them, or say: The documents do not say.") -> answer ->
checks: exact abstention, cited documents were retrieved, every figure appears in the cited
documents -> optional judge on faithfulness.

## Module boundaries

- The evaluation reads only the fixed corpus in `data/fnb`, `cnc`, `jewellery`. Uploads cannot
  move a reported number.
- The app never writes outside `data/uploads/`.
- The API key is read in exactly one place per entry point and never written to disk.
