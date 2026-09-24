# Cost to serve and time to deploy: the estimate before any live run

Written by `python cost_model.py --estimate` on 2026-09-24. Free: no key, no model call.
Generation model `openai/gpt-4o-mini` at $0.15/1M in, $0.6/1M out (prices dated 2026-09-21; source: A1 Part 1 notebook (OpenRouter list price)).

**Input tokens are ESTIMATED** from the actual prompts: the grounded system prompt plus the notes each config really retrieves for the 20 scored questions, at 4 characters per token. **Output tokens are ASSUMED** (90 per answer). `python run_eval.py --run` replaces both with the API's own usage counts, and `python cost_model.py` then writes `results/cost_model.md` from those.

## Layer 1: calls x tokens x price

| user action | model calls | input tokens (est.) | output tokens (assumed) | $ per action |
|---|---|---|---|---|
| ask a question: `shipped` (what the app ships) | 1 | 1,679 | 90 | $0.00031 |
| ask a question: `tfidf_k5` (the keyword baseline) | 1 | 1,731 | 90 | $0.00031 |
| file an upload (classify + impact brief) | 2 | 2,033 | 310 | $0.00049 |

A question the shipped system hands to a person below the confidence threshold makes **zero** model calls. Embedding is local and free per call.

## Layer 2: why the pass rate, not the token price, sets the cost

A wrong or declined answer is priced as a person spending 15 minutes at $40/h = $10.00 (an ASSUMPTION in config.py) -- about 32,693x the model cost of one question. The pass rate is only known after the live run, so this is the sensitivity, not a claim:

| answer pass rate | cost per successful answer | monthly at 200 questions | monthly at 2,000 questions |
|---|---|---|---|
| 100% | $0.0003 | $0.06 | $0.61 |
| 95% | $0.5003 | $100.06 | $1,000.61 |
| 90% | $1.0003 | $200.06 | $2,000.61 |
| 85% | $1.5003 | $300.06 | $3,000.61 |
| 80% | $2.0003 | $400.06 | $4,000.61 |

Context, not a like-for-like saving: the problem statement puts cross-division synthesis at 3-5 business days per weekly cycle, about $5,542/month of analyst time at these assumptions. Tanya answers questions; it does not replace the report, and a person still reviews its output.

## Time to deploy, measured on this machine

Embedder: local embeddings (all-MiniLM-L6-v2) -- matches MEANING.

| step | time | notes |
|---|---|---|
| `pip install -r requirements.txt` | minutes | one-off; dominated by torch (CPU build) |
| first embedding-model download | one-off, ~90 MB | cached by sentence-transformers after that |
| import the embedding stack | 5.8 s | measured |
| load the model and index 18 documents (3 indexes: plain, titled, keyword) | 8.5 s | measured; the app builds 1 index, once per session |
| add one document through the app | about 2 model calls + one re-index | measured index time above |

What it would take for real (an estimate, not measured): connecting each division's document store and its access control, which this project deliberately does not do (fictional corpus). Code-wise the retrieval is domain-agnostic: point `config.DOC_ID_TO_PATH` at other documents and re-run `python data/check_my_data.py`.
