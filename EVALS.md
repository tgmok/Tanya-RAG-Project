# The evals, explained

What is tested, what grades it, and where each result lands. These evals were written while the
system was being built, and every number in the README and the report comes from a file in
`results/`.

## What is evaluated

| stage | the question it answers | graded by | result |
|---|---|---|---|
| retrieval | do the retrieved notes cover every division and document a question needs (recall, MRR)? 13 setups, every miss diagnosed | code | `results/retrieval_recall.md` |
| chunk size | why 200-word chunks | code | `results/chunk_sweep.md` |
| answer correctness | is every key fact present? | code, against `data/eval_key_facts.json` | `results/summary.md` |
| answer faithfulness | is every claim supported by the notes? | a judge from a different model family (`gemini-2.5-flash`); its exact prompt is `docs/JUDGE_PROMPT.md` | `results/summary.md` |
| the judge itself | does it agree with a person? | my own grading of 10 answers per check: precision, recall, Cohen's kappa | `results/judge_agreement.md` |
| abstention | how often Tanya declines, and whether each decline was right | code | `results/summary.md` |
| silent failures | answers given although the needed documents were not retrieved | code | `results/summary.md` |
| guardrails | 45 named cases, including an attack document filed into the index, mapped to the OWASP 2026 categories | code | `results/guardrails.md` |
| leakage | does a question already contain its own answer? | code | `results/leakage.md` |
| cost | cost per successful answer, break-even against answering by hand, kill condition | code | `results/cost_estimate.md`, `results/cost_model.md` |
| the instruments | are the checkers themselves right? | `self_test.py` | printed |

Every answer the final run produced, with its verdicts, is in `results/answers.json`.

## The question sets

43 questions in five sets, each reported separately: main (23, fixed before anything ran), false
premise (2), break-it (6), partially answerable (6) and independent (6). The files are described in
`data/README.md`; every question, why it is there and what grades it is in
`docs/EVALUATION_SET.md`; what a good answer looks like is in `docs/GOOD_RUN.md`.

The comparison is always against the same baseline: keyword (TF-IDF) search over the same chunks, a
non-AI method.

## Running them

Free, no API key:

```bash
python self_test.py                      # the instruments
python run_guardrails.py                 # the guardrail checklist
python run_eval.py --retrieval-only      # retrieval, 13 setups
python run_eval.py --chunk-sweep         # chunk size
python run_eval.py --leakage             # leakage
python cost_model.py --estimate          # cost
python run_eval.py --dry-run --yes       # the whole live path with a fake model
```

Live, with an OpenRouter key (about $0.31; it prints an estimate and asks first):

```bash
python run_eval.py --run                 # answers: correctness, faithfulness, abstention
python run_eval.py --agreement           # after hand-grading the spot-check that --run writes
```

`harness.py` holds the question loading, the retrieval setups, the code checks, the judge call and
the aggregation; `run_eval.py` is the entry point.

## Targets and results

The targets and what was reached are in the README, under "Metrics: targeted and reached".

## What these evals cannot tell you

- **The sample is small.** With 20 scored questions, one answer is five points, so 84% faithfulness
  against an 85% target is within noise.
- **One author.** The documents, the designed questions and the key facts come from the same hand;
  only five questions were written by another model.
- **Synthetic documents.** They are tidier than real ones and share reference ids by design.
- **The judge was checked on 20 verdicts.** That is enough to trust its direction, not its decimals.
