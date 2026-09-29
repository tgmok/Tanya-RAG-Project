# Cost to serve and time to deploy: the estimate before any live run

Written by `python cost_model.py --estimate` on 2026-09-29. Free: no key, no model call.
Generation model `openai/gpt-4o-mini` at $0.15/1M in, $0.6/1M out (prices dated 2026-09-21; source: A1 Part 1 notebook (OpenRouter list price)).

**Input tokens are ESTIMATED** from the actual prompts: the grounded system prompt plus the notes each config really retrieves for the 20 scored questions, at 4 characters per token. **Output tokens are ASSUMED** (90 per answer). `python run_eval.py --run` replaces both with the API's own usage counts, and `python cost_model.py` then writes `results/cost_model.md` from those.

## Layer 1: calls x tokens x price

| user action | model calls | input tokens (est.) | output tokens (assumed) | $ per action |
|---|---|---|---|---|
| ask a question: `shipped` (what the app ships) | 1 | 2,271 | 90 | $0.00039 |
| ask a question: `tfidf_k5` (the keyword baseline) | 1 | 1,731 | 90 | $0.00031 |
| ask a question: `full_context` (all 18 documents in the prompt, no retrieval) | 1 | 5,870 | 90 | $0.00093 |
| file an upload (classify + impact brief) | 2 | 2,056 | 310 | $0.00049 |

A question the shipped system hands to a person below the confidence threshold makes **zero** model calls. Embedding is local and free per call.

**Retrieval against long context.** At 18 documents the whole corpus fits in one prompt, which is Class 2's rule for skipping retrieval, and it costs only 2.6x the tokens of the shipped retrieval. That is the honest case for long context here. Retrieval is chosen for what the pilot stands for: every division's documents over years will not fit, the long-context cost grows with the corpus while retrieval does not, and retrieval is where a real deployment would enforce which division's documents a reader may see.

## Layer 1, continued: a person checks every answer

Every answer is a draft that a person reads against its cited notes before using it: 3 minutes at $40/h = $2.00 (an ASSUMPTION in config.py), about 5,067x the model cost of the question. This is the human-in-the-loop gate, priced: it is paid on right answers too.

## Layer 2 and the break-even against answering by hand

A wrong or declined answer is redone by hand: 15 minutes = $10.00, the same work as answering the question without Tanya, the no-AI alternative. The course's break-even, p = 1 - (manual - layer 1) / redo, puts it at **20%**: Tanya is cheaper than answering by hand whenever more than 20% of its answers are right.

Measured: 85% (answer correctness in the final evaluation run, `results/summary.md`), 4 times the break-even, so the decision is robust rather than a knife-edge. At 85%, checking an answer could take up to 13 minutes before answering by hand became cheaper.

The break-even moves with the minutes the check takes, far more than with anything the model costs, which is why every answer carries its citations and the notes it drew on: they are what keep the check short.

| minutes to check one answer | break-even success rate |
|---|---|
| 1 | 7% |
| 3 (assumed) | 20% |
| 5 | 33% |
| 10 | 67% |
| 15 | 100% |

## Layer 3: fixed monthly, and the month in total

| fixed cost (ASSUMPTIONS, config.py) | $ per month |
|---|---|
| hosting: one small cloud VM for the Streamlit app | $20.00 |
| upkeep: 4 hours a month re-running the free checks and updating documents | $160.00 |
| re-running the answer-level evaluation after each change, about 4 a month | $1.00 |
| **total** | **$181.00** |

| answer success rate | cost per successful answer | month at 200 questions | month at 2,000 questions |
|---|---|---|---|
| 100% | $2.00 | $581 | $4,182 |
| 90% | $3.00 | $781 | $6,182 |
| 85% (measured) | $3.50 | $881 | $7,182 |
| 70% | $5.00 | $1,181 | $10,182 |
| 50% | $7.00 | $1,581 | $14,182 |
| answering every question by hand | $10.00 | $2,000 | $20,000 |

Layer 3 is spread over more questions as volume grows, so the case for Tanya strengthens with volume; the check and the redo never amortise. Below about 28 questions a month, the fixed cost alone makes answering by hand cheaper.

## Kill condition, written before a pilot

Class 5's last gate: capture the baseline now and write down what would make us stop. Re-run the fixed 20-question set after every change, and:

1. if answer correctness falls below the keyword baseline's (75% in the same run), switch to keyword retrieval: it is simpler, needs no embedding model, and on that result it won;
2. if it falls below the 20% break-even, or reviewers report the check taking longer than it would take to answer by hand, stop and answer by hand.

## Context: the weekly report

The problem statement puts cross-division synthesis at 3-5 business days per weekly cycle, about $5,542/month of analyst time at these assumptions. That is context, not a like-for-like saving: Tanya answers questions, it does not replace the report.

## Time to deploy, measured on this machine

Embedder: local embeddings (all-MiniLM-L6-v2) -- matches MEANING.

| step | time | notes |
|---|---|---|
| `pip install -r requirements.txt` | minutes | one-off; dominated by torch (CPU build) |
| first embedding-model download | one-off, ~90 MB | cached by sentence-transformers after that |
| import the embedding stack | 6.2 s | measured |
| load the model and index 18 documents (3 indexes: plain, titled, keyword) | 8.4 s | measured; the app builds 1 index, once per session |
| add one document through the app | about 2 model calls + one re-index | measured index time above |

What it would take for real (an estimate, not measured): connecting each division's document store and its access control, which this project deliberately does not do (fictional corpus). Code-wise the retrieval is domain-agnostic: point `config.DOC_ID_TO_PATH` at other documents and re-run `python data/check_my_data.py`.
