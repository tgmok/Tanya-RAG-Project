# The data, explained

Everything Tanya reads, and everything it is tested on, is in this folder. None of it is real
company data: TGMOK Holdings is fictional.

## The corpus: what Tanya answers from

- `fnb/`, `cnc/`, `jewellery/`: 18 documents, 6 per division (procedures, a contract summary,
  maintenance and calibration logs, financial reports, policies). Each file name starts with the id
  Tanya cites, for example `fnb/fnb-01_packaging_change_sop.md`.
- **Synthetic.** An LLM (Claude) wrote the documents from the prompts in `generation_prompts.md`,
  so the corpus can be regenerated. It holds no personal data.
- **Built around three cross-division links**, each split across divisions so that one division's
  documents cannot answer the question alone:
  - H1: a packaging change in F&B needs new tooling from CNC.
  - H2: the Jewellery division finances the other two.
  - H3: an F&B rush order forces CNC to reprioritise its own orders.
- `data_dictionary.md` lists every document, its division, and the link facts it carries.

## The questions: what Tanya is tested on

| file | what it holds | questions |
|---|---|---|
| `eval_questions.json` | the main set, fixed before anything ran: 11 cross-division, 9 single-division, 3 the documents cannot answer | 23 |
| `eval_key_facts.json` | the facts each answer must contain to count as correct | |
| `extra_questions.json` | false premise: the question assumes something untrue | 2 |
| `breaker_questions.json` | deliberate attempts to break retrieval | 6 |
| `partial_questions.json` | partially answerable: one part is in the documents, the other is in none | 6 |
| `independent_questions.json` | IND1 to IND5 written by another model (ChatGPT) from the documents alone; IND6 by the author | 6 |

Every question, why it is there and what grades it: `docs/EVALUATION_SET.md`. How the evaluation
runs: `EVALS.md` at the repository root.

## The real-data check

`validation_real/` holds 8 real records per division from public datasets, kept out of the corpus.
They test whether the method transfers beyond synthetic documents. Sources and limits are in
`validation_real/README_validation.md`.

## Uploads

- `sample_uploads/`: the two files used in the demo, a client onboarding brief and a supplier note
  carrying a hidden instruction (a prompt-injection attack).
- `uploads/`: whatever is filed through the app. Git ignores it and the evaluation never reads it,
  so nothing done in the app can move a reported number.

## Checking the data

```bash
python data/check_my_data.py    # corpus, manifest, answer key and key facts hang together
python self_test.py             # every key fact appears in its source documents
```

## Limits

- The corpus is synthetic and shares reference ids by design, which flatters reference-following.
- The documents, the designed questions and the key facts come from the same hand; only IND1 to
  IND5 were written elsewhere.
- The real-data slices are small, and the jewellery one checks pricing plausibility only.
