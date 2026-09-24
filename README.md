# Tanya: a cross-division RAG assistant for TGMOK Holdings

PE6201 Emerging AI Technologies · End-of-Course Project (individual) · Trixie Grace Mok

Tanya answers leadership questions from the internal documents of a fictional conglomerate with
three divisions (F&B contract manufacturing, CNC precision machine parts, gold jewellery), cites
the documents it used, says "The documents do not say." when they don't, and hands a question to
a person when retrieval confidence is too low to answer at all. It can also take a newly uploaded
document, route it to the divisions it affects (a person confirms), and brief leaders on what it
connects to in the other divisions.

The business and technical trade-off analysis is `docs/TRADEOFF_ANALYSIS.md`.

## Clone to a reproduced run

Everything in the first block runs with **no API key** (and no network after a one-off ~90 MB
download of the `all-MiniLM-L6-v2` embedder).

```bash
pip install -r requirements.txt          # read the torch note inside first
python data/check_my_data.py             # corpus, answer key and key facts hang together
python self_test.py                      # the evaluation instruments themselves are sound
python run_guardrails.py                 # every built guardrail against 28 named cases
python run_eval.py --retrieval-only      # recall of 9 retrieval setups, every miss diagnosed
python run_eval.py --chunk-sweep         # why 200-word chunks
python run_eval.py --leakage             # does a question already contain its own answer?
python cost_model.py --estimate          # calls x tokens x price, and time to deploy
python run_eval.py --dry-run --yes       # the whole live path with a fake model
streamlit run app.py                     # the app; retrieval works without a key
```

The answer-level evaluation needs a key (it prints an estimate, about $0.62, and asks first):

```bash
python run_eval.py --run                 # shipped system vs keyword baseline -> results/summary.md
python run_eval.py --agreement           # after hand-grading results/judge_spotcheck.json
python cost_model.py                     # measured cost per successful answer
python demo_citation_fix.py              # the bug from the screen recordings, re-run
```

The key is read from `OPENROUTER_API_KEY`, or from an untracked `OpenRouter_api.txt` in this
folder (it is in `.gitignore`), or asked for with a hidden prompt. It is never written anywhere.

## Layout

`CODE_MAP.md` has what each file does, a reading order and every command.

```
README.md                  this file
CODE_MAP.md                what each file does, reading order, commands, current results
requirements.txt           pinned; read the torch note inside before installing
config.py                  THE one place to change a setting: models, chunking, top-k, thresholds,
                           prices, cost assumptions, the corpus manifest

rag_core.py                the pipeline: load, chunk, embed, retrieve, grounded answer,
                           upload classification, impact brief. Shared by app, eval and demo.
guardrails.py              every Section 8 mitigation that is code: token cap, injection scan,
                           confidence hand-off, exact abstention, figure check, fake-citation check
app.py                     Streamlit interface: upload -> scan -> classify -> confirm -> brief -> chat
doc_parser.py              PDF/DOCX to text, no model calls

run_eval.py                the evaluation entry point                      <- what a marker runs
harness.py                 question sets, 9 retrieval configs, code checks, judge, aggregation
run_guardrails.py          guardrail checklist             -> results/guardrails.md
self_test.py               checks the instruments, not the system
cost_model.py              cost per query, per success, and time to deploy -> results/cost_*.md
demo_citation_fix.py       the recorded failure, re-run    -> results/citation_fix.md
make_docs.py               regenerates docs/EVALUATION_SET.md and the blind question pack
Tanya_RAG_Notebook.ipynb   the smallest first version, and the evaluation as a narrative

data/
    fnb/ cnc/ jewellery/       the graded corpus: 18 synthetic documents, 6 per division
    generation_prompts.md      the prompts that produced the corpus, so it can be regenerated
    data_dictionary.md         every document, its division, and the hook facts it carries
    eval_questions.json        the answer key: 23 questions, fixed before anything ran
    eval_key_facts.json        the facts each answer must contain (answer correctness)
    extra_questions.json       near-miss questions (a fact the corpus nearly contains)
    breaker_questions.json     deliberate attempts to break retrieval
    independent_questions.json written by a different model from the documents alone
    check_my_data.py           run after every data change
    validation_real/           small real-world slices, one per division, kept out of the corpus
    sample_uploads/            the document used to demo and test the upload path
    uploads/                   added through the app; ignored by git AND by the evaluation

docs/
    TRADEOFF_ANALYSIS.md       the business & technical trade-off analysis (the hand-in)
    SYSTEM_FLOW.md             one request end to end, with every guardrail on the path
    EVALUATION_SET.md          every question, what it is for, and which check grades it
    JUDGE_PROMPT.md            the exact prompt the judge receives: a described instrument
    GOOD_RUN.md                what a good answer looks like, as testable statements
    BLIND_QUESTION_PACK.md     the documents-only pack used to write the independent questions

results/                   every number in the write-up comes from a file here
    retrieval_recall.md        9 configs, every miss diagnosed, the abstention-threshold curve
    chunk_sweep.md             why 200/50 chunks
    leakage.md                 which questions contain their own answer, before/after stripping
    notebook_run.md            answer-level results of the final notebook run, copied verbatim
    guardrails.md              the Section 8 checklist
    cost_estimate.md           cost per question and per upload, and time to deploy (free)
    summary.md                 answer-level results (after --run)
    cost_model.md              measured cost per successful answer (after --run)
    judge_agreement.md         the judge's precision and recall against hand labels (after --agreement)
    citation_fix.md            the recorded bug, re-run (after demo_citation_fix.py)
```

## What is measured

- **Retrieval, free:** did the retrieved notes cover every division and every document a question
  needs? Nine setups, including the shipped one, the keyword baseline and "all documents in the
  prompt", with every miss diagnosed by rank and score.
- **The baseline is keyword search over the same chunks** (`tfidf_k5`), a non-AI method. A model
  with no retrieval is not the baseline: it has never seen these fictional documents, so it scores
  near zero whatever the retrieval does, and teaches nothing.
- **Answers, on the same 20 questions, two ways:** correctness (every key fact present, a code
  check against `data/eval_key_facts.json`) and faithfulness (every claim supported by the notes,
  judged by a different model family, prompt committed in `docs/JUDGE_PROMPT.md`). Faithfulness
  alone is won by quoting a chunk back; correctness alone cannot tell a grounded answer from a
  lucky one.
- **Abstention, as two numbers:** how often it declines, and whether the declines were right (out
  of scope, or the needed documents were not retrieved). Plus the **silent failure**: answering
  although the needed documents were not in front of the model.
- **The judge is measured too:** precision and recall against answers graded by hand.
- **Sets reported separately:** main (designed before anything ran), near-miss, breakers, and
  independent (written by another model from the documents alone).

## Limits we found

- **Faithfulness misses its target on the final run: 80% against 85%**, with answer correctness
  also 80%. The keyword baseline was more faithful (95%) and slightly less correct (75%), so
  embeddings earn their place on coverage and correctness, not on faithfulness
  (`results/notebook_run.md`, 20 questions, one judge pass, the judge not yet hand-checked).
- **Titling fixes the division, not the document.** The shipped retrieval covers every needed
  division on all 11 cross-division questions (plain top-5: 91%), but document recall stays at
  88% either way. It still misses a needed document on 4 of 31 scored questions; three are the
  same CNC tooling spec (`cnc-01`), which for CD1 ranks #8 of 21 chunks at 0.432 against a 0.477
  cutoff.
- **The keyword baseline beats embeddings on document recall** (91% vs 88%). The non-AI baseline
  is not a pushover here, and the answer-level comparison is what decides whether embeddings earn
  their place.
- **The mitigation first proposed in the problem statement hurts.** Classifying the query by
  division before retrieving cuts cross-division recall to 45%, against 91% for the same
  retrieval without it, so it is not used.
- **A retrieval-score threshold is a weak abstention signal.** At the shipped 0.45 it catches 2 of
  6 unanswerable questions and wrongly hands off 1 of 31 answerable ones; answerable and
  plausible-but-absent questions overlap in score. It is a backstop, not the defence.
- **Confident hallucination when retrieval misses.** An earlier live run found the model answering
  anyway when the needed document was not retrieved, including one invented component. The figure
  check catches invented numbers, dates and ids, but not an invented claim with none in it; the
  silent-failure count in `results/summary.md` is how that shape is detected.
- **Uploads are untrusted input.** A pattern scan routes a suspicious upload to a person instead of
  the automatic classifier (OWASP LLM01), with no false positives on the 18 real documents. A
  document a person chooses to file anyway is then retrievable into answers, where the grounded
  prompt is the remaining defence.
- **The corpus is synthetic and was written by an LLM.** The validation slices are small (8 records
  each), and the jewellery one checks pricing plausibility only.
- **Not everything is independent.** The designed questions and key facts come from the same hand
  that wrote the corpus; only the independent set was written elsewhere.
- **Machine-specific:** `torch` 2.13 and later crashed at import on the author's AMD Ryzen (Zen4)
  CPU, so 2.2.2 is pinned, which in turn needs `numpy` below 2.

## Extending the evaluation set

1. Add a document under `data/<division>/`, register it in `config.DOC_ID_TO_PATH`, then run
   `python data/check_my_data.py`.
2. Write the question into `data/eval_questions.json` and its key facts into
   `data/eval_key_facts.json` **before** running the system on it.
3. `python self_test.py` (every fact must appear in its source documents), then
   `python make_docs.py`, then `python run_eval.py --retrieval-only` and `--run`.

## Sources and acknowledgements

- The A1 starter notebooks (course-provided) are the scaffold for the retrieval and judge cells
  in `Tanya_RAG_Notebook.ipynb`.
- Claude (Anthropic) wrote the corpus and much of the code with the author. ChatGPT wrote the
  independent questions IND1 to IND5 from the blind pack.
