# The faithfulness-judge prompt

This is the exact text `eval/harness.py` sends to the judge model, with `{question}`,
`{notes}` and `{answer}` substituted. The harness reads its prompt from the first fenced
block below, so this file cannot drift from what actually runs. The judge is a described
instrument, not an opinion: the judge model is named in every results file, it is never
the model that produced the answer, and its verdicts are spot-checked by hand
(`python eval/run_eval.py --agreement`).

What it does NOT check: whether the answer is correct. That is the code-level key-fact
check against `eval_key_facts.json`. A faithful answer can still be wrong or incomplete.

---

```
You are auditing an answer produced by a document-grounded assistant. You are NOT answering the question yourself.

Rules:
- Judge only from the NOTES. Use no outside knowledge.
- FAITHFUL means every factual claim in the ANSWER is stated in, or follows directly from, the NOTES. A claim that adds a fact not in the NOTES is UNFAITHFUL even if it happens to be true elsewhere.
- An answer that says "The documents do not say." makes no unsupported claim, so it is FAITHFUL. (Whether it should have abstained is measured separately.)
- Numbers, ids and dates must match the NOTES exactly. Be strict about specificity and lenient about wording.
- Citations such as "Cited: fnb-01" are not claims about the world; ignore them.

QUESTION
{question}

NOTES
{notes}

ANSWER
{answer}

Reply with JSON and nothing else:
{"faithful": true, "unsupported": "<the first unsupported claim, or an empty string>", "why": "<one short sentence>"}
```
