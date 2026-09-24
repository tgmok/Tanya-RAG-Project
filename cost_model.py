"""Cost to serve, in the three-layer shape of the course's cost calculator:

    layer 1  variable model cost per query  = calls x (input tokens x price + output tokens x price)
    layer 2  failure cost per query         = (1 - success rate) x cost of a person redoing the answer
    cost per successful answer              = layer 1 + layer 2
    monthly                                 = cost per successful answer x volume

    python cost_model.py --estimate   free, no key: prices the ACTUAL prompts the shipped system and
                                      the keyword baseline send, and times the one-off setup
                                      (time-to-deploy)                    -> results/cost_estimate.md
    python cost_model.py              after `python run_eval.py --run`: measured tokens and
                                      measured pass rates                 -> results/cost_model.md

Prices and cost-model assumptions live in config.py (one dated block). Serving cost counts only
the generation model: embeddings run locally (no per-call price) and the judge is an evaluation
instrument, not part of answering a user, so its cost is reported separately.
"""
import argparse
import importlib
import json
import sys
import time
from datetime import date

from config import (ANALYST_USD_PER_HOUR, CHARS_PER_TOKEN, CYCLES_PER_MONTH, DATA_DIR,
                    EST_ANSWER_TOKENS, GEN_MODEL, HOURS_PER_DAY, HUMAN_REVIEW_MINUTES,
                    MANUAL_CYCLE_DAYS, PRICES, PRICES_DATED, RESULTS_DIR, VOLUMES)


def variable_cost(model, tokens_in, tokens_out):
    p = PRICES[model]
    return tokens_in / 1e6 * p["in"] + tokens_out / 1e6 * p["out"]


def failure_cost_usd():
    return ANALYST_USD_PER_HOUR * HUMAN_REVIEW_MINUTES / 60.0


def cost_per_successful(var_usd, success_rate):
    assert 0.0 <= success_rate <= 1.0
    return var_usd + (1.0 - success_rate) * failure_cost_usd()


def monthly(per_success_usd, volume):
    return per_success_usd * volume


def manual_monthly_usd():
    return MANUAL_CYCLE_DAYS * HOURS_PER_DAY * ANALYST_USD_PER_HOUR * CYCLES_PER_MONTH


def est_tokens(text):
    return len(text) / CHARS_PER_TOKEN


def estimate_run(gen_model, judge_model, n_questions, n_scored, configs, do_judge=True,
                 words_sent=None, no_retrieval_floor=False):
    """Rough UPPER-bound dollars for a live evaluation run, printed before anything is spent.
    words_sent: {config: average words of notes sent}, measured by the free retrieval report in the
    same run, so the estimate tracks the real chunk size. None if a model has no price."""
    if gen_model not in PRICES or (do_judge and judge_model not in PRICES):
        return None
    words_sent = words_sent or {}
    total = n_questions * variable_cost(gen_model, 60, 100) if no_retrieval_floor else 0.0
    for c in configs:
        tin = words_sent.get(c, 1200) * 1.4 + 250          # ~1.4 tokens/word + system prompt
        total += n_questions * variable_cost(gen_model, tin, 150)
        if do_judge:
            total += n_scored * variable_cost(judge_model, tin + 500, 700)  # judge models may 'think'
    return total


# ---------------------------------------------------------------------------
# --estimate: free, before any live run
# ---------------------------------------------------------------------------

def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def run_estimate():
    import harness as H
    import rag_core
    import doc_parser

    t_start = time.perf_counter()
    importlib.import_module("sentence_transformers")  # timed: the heaviest import in the stack
    t_import = time.perf_counter() - t_start
    idx, t_index = _timed(H.build_indexes)
    using = idx["plain"]["embedder"].using
    main = [q for q in H.load_questions(include_extra=False, include_independent=False)
            if q["kind"] != "out_of_scope"]

    def prompt_tokens(config):
        """(average whole-prompt tokens, average tokens per retrieved note) over the 20 questions."""
        whole, per_note = [], []
        for q in main:
            hits = H.retrieve_config(config, q["question"], idx)
            context = "\n\n".join(f"[{i+1}] ({h['doc_id']}) {h['text']}" for i, h in enumerate(hits))
            user = f"NOTES:\n{context}\n\nQUESTION: {q['question']}"
            whole.append(est_tokens(rag_core.GROUNDED) + est_tokens(user))
            per_note.append(est_tokens(context) / max(1, len(hits)))
        return sum(whole) / len(whole), sum(per_note) / len(per_note)

    measured = {c: prompt_tokens(c) for c in (H.SHIPPED, H.BASELINE)}
    ask = {c: m[0] for c, m in measured.items()}
    note_tokens = measured[H.SHIPPED][1]

    # Filing an upload is two calls: classify the raw text, then the cross-division impact brief.
    sample = DATA_DIR / "sample_uploads" / "meadowfield_snacks_onboarding.docx"
    up_text = doc_parser.extract_text(sample.name, sample.read_bytes())
    t_classify_in = est_tokens(rag_core.CLASSIFY_SYSTEM) + est_tokens(up_text[:6000])
    # the brief sends the upload's opening 400 characters plus 4 retrieved notes (k=4 in rag_core)
    t_brief_in = est_tokens(rag_core.IMPACT_SYSTEM) + est_tokens(up_text[:400]) + 4 * note_tokens

    g = GEN_MODEL
    per_q = {c: variable_cost(g, t, EST_ANSWER_TOKENS) for c, t in ask.items()}
    per_upload = variable_cost(g, t_classify_in, 60) + variable_cost(g, t_brief_in, 250)

    L = ["# Cost to serve and time to deploy: the estimate before any live run", "",
         f"Written by `python cost_model.py --estimate` on {date.today()}. Free: no key, no model call.",
         f"Generation model `{g}` at ${PRICES[g]['in']}/1M in, ${PRICES[g]['out']}/1M out "
         f"(prices dated {PRICES_DATED}; source: {PRICES[g]['source']}).", "",
         "**Input tokens are ESTIMATED** from the actual prompts: the grounded system prompt plus the notes "
         f"each config really retrieves for the 20 scored questions, at {CHARS_PER_TOKEN} characters per token. "
         f"**Output tokens are ASSUMED** ({EST_ANSWER_TOKENS} per answer). `python run_eval.py --run` "
         "replaces both with the API's own usage counts, and `python cost_model.py` then writes "
         "`results/cost_model.md` from those.", "",
         "## Layer 1: calls x tokens x price", "",
         "| user action | model calls | input tokens (est.) | output tokens (assumed) | $ per action |",
         "|---|---|---|---|---|",
         f"| ask a question: `{H.SHIPPED}` (what the app ships) | 1 | {ask[H.SHIPPED]:,.0f} | "
         f"{EST_ANSWER_TOKENS} | ${per_q[H.SHIPPED]:.5f} |",
         f"| ask a question: `{H.BASELINE}` (the keyword baseline) | 1 | {ask[H.BASELINE]:,.0f} | "
         f"{EST_ANSWER_TOKENS} | ${per_q[H.BASELINE]:.5f} |",
         f"| file an upload (classify + impact brief) | 2 | {t_classify_in + t_brief_in:,.0f} | 310 | "
         f"${per_upload:.5f} |",
         "", "A question the shipped system hands to a person below the confidence threshold makes "
         "**zero** model calls. Embedding is local and free per call.", "",
         "## Layer 2: why the pass rate, not the token price, sets the cost", "",
         f"A wrong or declined answer is priced as a person spending {HUMAN_REVIEW_MINUTES} minutes at "
         f"${ANALYST_USD_PER_HOUR:.0f}/h = ${failure_cost_usd():.2f} (an ASSUMPTION in config.py) -- about "
         f"{failure_cost_usd() / per_q[H.SHIPPED]:,.0f}x the model cost of one question. The pass rate is "
         "only known after the live run, so this is the sensitivity, not a claim:", "",
         "| answer pass rate | cost per successful answer | monthly at " +
         " | monthly at ".join(f"{v:,} questions" for v in VOLUMES) + " |",
         "|---|---|" + "---|" * len(VOLUMES)]
    for pr in (1.00, 0.95, 0.90, 0.85, 0.80):
        ps = cost_per_successful(per_q[H.SHIPPED], pr)
        L.append(f"| {pr:.0%} | ${ps:.4f} | " + " | ".join(f"${monthly(ps, v):,.2f}" for v in VOLUMES) + " |")
    L += ["", f"Context, not a like-for-like saving: the problem statement puts cross-division synthesis "
          f"at 3-5 business days per weekly cycle, about ${manual_monthly_usd():,.0f}/month of analyst time "
          f"at these assumptions. Tanya answers questions; it does not replace the report, and a person "
          "still reviews its output.", "",
          "## Time to deploy, measured on this machine", "",
          f"Embedder: {using}.", "",
          "| step | time | notes |", "|---|---|---|",
          "| `pip install -r requirements.txt` | minutes | one-off; dominated by torch (CPU build) |",
          "| first embedding-model download | one-off, ~90 MB | cached by sentence-transformers after that |",
          f"| import the embedding stack | {t_import:.1f} s | measured |",
          f"| load the model and index 18 documents (3 indexes: plain, titled, keyword) | {t_index:.1f} s | "
          "measured; the app builds 1 index, once per session |",
          "| add one document through the app | about 2 model calls + one re-index | measured index time above |",
          "", "What it would take for real (an estimate, not measured): connecting each division's document "
          "store and its access control, which this project deliberately does not do (fictional corpus). "
          "Code-wise the retrieval is domain-agnostic: point `config.DOC_ID_TO_PATH` at other documents and "
          "re-run `python data/check_my_data.py`.", ""]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "cost_estimate.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwritten: {RESULTS_DIR / 'cost_estimate.md'}")


# ---------------------------------------------------------------------------
# Measured: after a live run
# ---------------------------------------------------------------------------

def run_measured():
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("results/summary.json not found. Run `python run_eval.py --run` first, or "
              "`python cost_model.py --estimate` for the free estimate.")
        sys.exit(1)
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    gen = s["gen_model"]
    if gen not in PRICES:
        print(f"No price for {gen}; add it to PRICES in config.py first.")
        sys.exit(1)

    lines = ["# Cost to serve: what one answer costs (measured)", "",
             f"Generation model: `{gen}`. Prices dated {PRICES_DATED} "
             f"(in {PRICES[gen]['in']}/1M, out {PRICES[gen]['out']}/1M; source: {PRICES[gen]['source']}).",
             "Tokens and pass rates are MEASURED (results/summary.json, the API's own usage counts). "
             "Labour numbers are ASSUMPTIONS (config.py). Success = the answer contains its key facts "
             "(answer correctness), main set only.", "",
             "| config | avg tokens in/out | layer 1 $/query | answer correctness | cost per successful answer |",
             "|---|---|---|---|---|"]
    rows = {}
    first_var = None
    for name, agg in s["configs"].items():
        var = variable_cost(gen, agg["avg_tokens_in"], agg["avg_tokens_out"])
        first_var = first_var or var
        main_agg = s.get("by_set", {}).get("configs", {}).get(name, {}).get("main", agg)
        succ = main_agg["key_fact_pass"] or 0.0
        per_success = cost_per_successful(var, succ)
        rows[name] = per_success
        lines.append(f"| {name} | {agg['avg_tokens_in']:.0f} / {agg['avg_tokens_out']:.0f} | "
                     f"${var:.5f} | {succ:.0%} | ${per_success:.4f} |")

    lines += ["", "## Monthly, at assumed volumes", "",
              "| config | " + " | ".join(f"{v:,} questions" for v in VOLUMES) + " |",
              "|---|" + "---|" * len(VOLUMES)]
    for name, ps in rows.items():
        lines.append(f"| {name} | " + " | ".join(f"${monthly(ps, v):,.2f}" for v in VOLUMES) + " |")

    lines += ["", "## What the failure term is doing", "",
              f"A wrong or abstained answer is priced as a person spending {HUMAN_REVIEW_MINUTES} minutes at "
              f"${ANALYST_USD_PER_HOUR:.0f}/h = ${failure_cost_usd():.2f}. That is about "
              f"{failure_cost_usd() / first_var:,.0f}x the model cost of a query, so the pass rate, not the "
              "token price, decides the cost per successful answer. Changing the config only pays for itself "
              "if it moves the pass rate.", "",
              "## Context: the manual process this aims to shorten", "",
              f"The problem statement puts cross-division synthesis at 3-5 business days per report cycle. At "
              f"{MANUAL_CYCLE_DAYS} days x {HOURS_PER_DAY} h x ${ANALYST_USD_PER_HOUR:.0f}/h x {CYCLES_PER_MONTH} "
              f"cycles/month that is about ${manual_monthly_usd():,.0f}/month of analyst time. This is context, "
              "not a like-for-like saving: Tanya answers questions, it does not replace the report, and a person "
              "still reviews its output.", ""]

    if s.get("judge_model") and s["judge_model"] in PRICES:
        jc = sum(variable_cost(s["judge_model"], a["judge_tokens_in"], a["judge_tokens_out"])
                 for a in s["configs"].values())
        lines += [f"Judge (`{s['judge_model']}`) cost for this whole evaluation run: about ${jc:.3f}. "
                  "Evaluation cost only; not part of serving a user.", ""]

    (RESULTS_DIR / "cost_model.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten: {RESULTS_DIR / 'cost_model.md'}   (as of {date.today()})")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--estimate", action="store_true", help="free: price the real prompts, time the setup")
    args = ap.parse_args()
    run_estimate() if args.estimate else run_measured()


if __name__ == "__main__":
    main()
