"""Cost-to-serve model for Tanya, in the three-layer shape of the course's cost calculator:

    layer 1  variable model cost per query     = input tokens x price + output tokens x price
    layer 2  failure cost per query            = (1 - success rate) x cost of a person redoing the answer
    cost per successful answer                 = layer 1 + layer 2
    monthly                                    = cost per successful answer x volume

Prices and labour numbers are DATA in one dated block below. Measured inputs (tokens, pass
rate) come from results/summary.json, written by `python eval/run_eval.py --run`.

Serving cost counts only the generation model: retrieval embeddings run locally (no per-call
price) and the judge is an evaluation tool, not part of answering a user. Judge cost is
reported separately.

    python eval/cost_model.py
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

# ---- PRICES, US$ per 1M tokens. Dated. VERIFY at openrouter.ai/models before quoting. ----
PRICES_DATED = "2026-09-21"
PRICES = {
    "openai/gpt-4o-mini": {"in": 0.15, "out": 0.60, "source": "your A1 Part 1 notebook (OpenRouter)"},
    "google/gemini-2.5-flash": {"in": 0.30, "out": 2.50, "source": "ASSUMPTION: list price as I recall it; verify"},
}

# ---- ASSUMPTIONS, not measurements. Edit these; every one changes the answer. ----
HUMAN_REVIEW_MINUTES = 15      # an analyst checking or redoing one wrong/abstained answer
ANALYST_USD_PER_HOUR = 40.0    # placeholder rate
MANUAL_CYCLE_DAYS = 4          # midpoint of "3-5 business days" in the problem statement
HOURS_PER_DAY = 8
CYCLES_PER_MONTH = 4.33        # weekly reports
VOLUMES = [200, 2000]          # questions per month


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


# Typical prompt sizes (input tokens) per retrieval config, for the pre-run estimate only.
# The whole corpus is about 3,200 words (roughly 5k tokens), which is why full_context is priced separately.
TYPICAL_PROMPT_TOKENS = {"naive_k3": 600, "naive_k5": 900, "titled_k5": 900, "parent_d3": 1800,
                         "tfidf_k5": 900, "balanced_2x3": 1100, "full_context": 5000}


def estimate_run(gen_model, judge_model, n_questions, n_scored, configs, do_judge=True):
    """Rough upper-bound dollars for a live run. None if a model has no price."""
    if gen_model not in PRICES or (do_judge and judge_model not in PRICES):
        return None
    total = n_questions * variable_cost(gen_model, 60, 100)            # no-retrieval baseline
    for c in configs:
        tin = TYPICAL_PROMPT_TOKENS.get(c, 1500)
        total += n_questions * variable_cost(gen_model, tin + 150, 150)
        if do_judge:
            total += n_scored * variable_cost(judge_model, tin + 500, 700)  # judge models may 'think'
    return total


def main():
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("results/summary.json not found. Run: python eval/run_eval.py --run")
        sys.exit(1)
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    gen = s["gen_model"]
    if gen not in PRICES:
        print(f"No price for {gen}; add it to PRICES first.")
        sys.exit(1)

    lines = [f"# Cost to serve: what one answer costs", "",
             f"Generation model: `{gen}`. Prices dated {PRICES_DATED} "
             f"(in {PRICES[gen]['in']}/1M, out {PRICES[gen]['out']}/1M; source: {PRICES[gen]['source']}).",
             "Tokens and pass rates are MEASURED (results/summary.json). Labour numbers are ASSUMPTIONS.", "",
             "| config | avg tokens in/out | layer 1 $/query | key-fact pass | cost per successful answer |",
             "|---|---|---|---|---|"]
    rows = {}
    first_var = None
    for name, agg in s["configs"].items():
        var = variable_cost(gen, agg["avg_tokens_in"], agg["avg_tokens_out"])
        first_var = first_var or var
        main_agg = s.get("by_set", {}).get("configs", {}).get(name, {}).get("main", agg)
        succ = main_agg["key_fact_pass"] or 0.0   # main set only
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
              f"${ANALYST_USD_PER_HOUR:.0f}/h = ${failure_cost_usd():.2f}. That is about {failure_cost_usd() / first_var:,.0f}x the model cost of a "
              "query, so the pass rate, not the token price, decides the cost per successful answer. "
              "Changing the config only pays for itself if it moves the pass rate.", "",
              "## Context: the manual process this aims to shorten", "",
              f"The problem statement puts cross-division synthesis at 3-5 business days per report cycle. At "
              f"{MANUAL_CYCLE_DAYS} days x {HOURS_PER_DAY} h x ${ANALYST_USD_PER_HOUR:.0f}/h x {CYCLES_PER_MONTH} "
              f"cycles/month that is about ${manual_monthly_usd():,.0f}/month of analyst time. This is context, "
              "not a like-for-like saving: Tanya answers questions, it does not replace the report, and a person "
              "still reviews its output.", ""]

    if s.get("judge_model"):
        if s["judge_model"] in PRICES:
            jc = sum(variable_cost(s["judge_model"], a["judge_tokens_in"], a["judge_tokens_out"])
                     for a in s["configs"].values())
            lines += [f"Judge (`{s['judge_model']}`) cost for this whole evaluation run: about ${jc:.3f}. "
                      "Evaluation cost only; not part of serving a user.", ""]

    (RESULTS_DIR / "cost_model.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten: {RESULTS_DIR / 'cost_model.md'}   (as of {date.today()})")


if __name__ == "__main__":
    main()
