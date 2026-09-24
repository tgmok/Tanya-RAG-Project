# Tanya: a cross-division RAG assistant for TGMOK Holdings

PE6201 Emerging AI Technologies, End-of-Course Project (individual). Tanya answers leadership
questions from the internal documents of a fictional conglomerate with three divisions (F&B
contract manufacturing, CNC precision machine parts, gold jewellery), cites the documents it
used, says "The documents do not say." when they don't, and can take a newly uploaded
document, route it to the divisions it affects, and brief leaders on what else it touches.

The business and technical trade-off analysis is `docs/TRADEOFF_ANALYSIS.md`. (`docs/ALIGNMENT.md`, my running log against the course documents, is deliberately not committed: it is a working notebook, not a deliverable.)

## Clone to a reproduced run

The first five commands need no API key and no network after the one-off model download
(about 90 MB, the `all-MiniLM-L6-v2` embedder).

```bash
pip install -r requirements.txt          # read the torch note inside first
python check_my_data.py                  # corpus, answer key and key facts hang together
python eval/self_test.py                 # the evaluation instruments themselves are sound
python eval/run_eval.py --retrieval-only # recall of 8 retrieval setups, with every miss diagnosed
python eval/run_eval.py --chunk-sweep    # why 200-word chunks
python eval/run_eval.py --leakage        # does a question already contain its own answer?
streamlit run webapp/app.py              # the upload-and-ask app (paste a key in the sidebar to generate answers)
```

Live evaluation (costs about $0.50 at most; it prints an estimate and asks first):

```bash
python eval/run_eval.py --run
python eval/run_eval.py --agreement      # after you hand-grade results/judge_spotcheck.json
python eval/cost_model.py
```

The key is read from `OPENROUTER_API_KEY`, or from an untracked `OpenRouter_api.txt` in this
folder (it is in `.gitignore`), or asked for with a hidden prompt. It is never written anywhere.

## Layout

See `CODE_MAP.md` for what each file does and a reading order.

```
README.md                   this file
CODE_MAP.md                 what each file does and a reading order
requirements.txt            pinned; read the torch note inside before installing
check_my_data.py            corpus + answer key + key facts hang together        <- run first
data_dictionary.md          every document, its division, and what it is for
generation_prompts.md       the prompts that produced the corpus, so it can be regenerated

webapp/
    rag_core.py             the whole pipeline in one file: load, chunk, embed, retrieve,
                            grounded answer, upload classification, impact snapshot, the
                            citation-content check, the confidence hand-off. Shared with eval.
    app.py                  Streamlit interface: upload -> classify -> confirm -> snapshot -> chat
    doc_parser.py           PDF/DOCX to text. No model calls.

eval/
    run_eval.py             the entry point                                      <- what a marker runs
    harness.py              question sets, 8 retrieval configs, code checks, judge call, aggregation
    self_test.py            checks the instruments themselves, not the system
    cost_model.py           three-layer cost per successful answer, from measured tokens
    make_docs.py            regenerates docs/EVALUATION_SET.md and the blind pack
    extra_questions.json    near-miss questions (a fact the corpus nearly, but does not, contain)
    breaker_questions.json  deliberate attempts to break retrieval
    independent_questions.json  written by ChatGPT from the documents alone, not by me

eval_questions.json         the designed answer key: 23 questions, fixed before anything ran
eval_key_facts.json         the facts each answer must contain -- correctness, not just faithfulness

data/fnb, cnc, jewellery/   18 synthetic documents, 6 per division (the graded corpus)
data/validation_real/       small real-world slices, one per division, kept out of the corpus
data/uploads/               added through the app; ignored by git AND by the evaluation

docs/
    TRADEOFF_ANALYSIS.md    the business & technical trade-off analysis (the hand-in)
    EVALUATION_SET.md       every question, what it is for, and which check grades it
    JUDGE_PROMPT.md         the exact prompt the judge receives; the judge is a described instrument
    GOOD_RUN.md             what a good run looks like, as testable statements
    SYSTEM_FLOW.md          one question end to end
    BLIND_QUESTION_PACK.md  the documents-only pack given to ChatGPT to write independent questions
    REVERT.md               how to remove the app and leave the graded corpus untouched

results/                    every number quoted in the write-up comes from a file here
    retrieval_recall.md     8 retrieval configs, every miss diagnosed, abstention threshold curve
    chunk_sweep.md          why 200/50 chunks
    leakage.md              which questions already contain their own answer, and the cost of stripping it
    summary.md              answer-level results (after a live run)

Tanya_RAG_Notebook.ipynb    the smallest first version, and the L1/L2 evaluation as a narrative
```

## What is measured

- **Retrieval, free:** did the retrieved notes cover every division and document a question
  needs? Eight setups, including a keyword (non-AI) baseline and "all documents in the prompt".
- **Answers, code checks (no model):** required key facts present, exact abstention on
  out-of-scope questions, citations only to retrieved documents, and every figure, date and id
  in the answer present in the cited documents.
- **Answers, judge (a different model family from the generator):** faithfulness to the notes,
  with the prompt committed in `docs/JUDGE_PROMPT.md` and a hand-graded agreement check.
- **Sets, reported separately:** main (designed), near-miss, breakers, and independent (five
  questions written by ChatGPT from the documents alone, one by the author). See
  `docs/EVALUATION_SET.md`.

## Limits we found

- **Top-3 retrieval misses a needed document often.** Cross-division recall is 64% at top-3,
  91% at top-5 plain, and 100% at top-5 with title-prefixed embedding (what the app ships).
  Document recall stays at 88% in all three: titling fixes which *division* is covered, not
  which *document*. The clearest miss is CD1, where the CNC tooling spec still ranks #6 of 21
  chunks at 0.466 against a 0.494 cutoff -- a near miss now, but still a miss.
- **A keyword baseline beats embeddings on document recall** (91% vs 88% at top-5), and ties
  them on cross-division recall (91%). The non-AI baseline is not a pushover here.
- **The mitigation in the problem statement, classifying the query by division before
  retrieval, hurts:** cross-division recall falls from 100% to 45%.
- **A retrieval-score threshold is a weak abstention signal.** Plausible-but-absent questions
  score 0.47 to 0.63, the same range as answerable ones (`results/retrieval_recall.md`).
- **The corpus is synthetic and was written by an LLM**, not adapted from public SOP templates
  as first proposed. The validation slices are small (8 records each), and the jewellery one
  validates pricing only, not document text.
- **Not everything is independent.** The designed questions and the key facts come from the same
  hand that wrote the corpus. Only the `independent` set was written elsewhere, and even its
  answer strings were derived with the assistant's help.
- **Uploaded documents are untrusted input** and there is no defence against instructions hidden
  in them yet (OWASP LLM01, Prompt Injection).
- **Machine-specific:** `torch` 2.13 and later crashed at import on the author's AMD Ryzen (Zen4)
  CPU, so 2.2.2 is pinned, which in turn needs `numpy` below 2.

## Sources and acknowledgements

- The A1 starter notebooks (course-provided) are the scaffold for the retrieval and judge cells
  in `Tanya_RAG_Notebook.ipynb`.
- Claude (Anthropic) wrote the corpus and much of the code with the author. ChatGPT wrote
  independent questions IND1 to IND5 from the blind pack.
