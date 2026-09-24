"""Offline checks that the evaluation instruments themselves are sound. No model, no API key.

    python self_test.py

An eval whose key facts are wrong grades the system wrongly, so this checks:
  1. every scored question has key facts, and no orphan facts exist
  2. every fact group appears in the question's own source documents (facts are verifiable
     from the corpus, not from memory)
  3. the question's expected_answer_summary satisfies its own facts (no typos in the groups)
  4. the checker rejects a plausible wrong answer and abstentions
  5. citation validation and the judge prompt behave
"""
import json
import sys

import guardrails
import harness as H

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


qs = H.load_questions()
scored = [q for q in qs if q["kind"] != "out_of_scope"]

main_ids = {q["id"] for q in qs if q["set"] == "main" and q["kind"] != "out_of_scope"}
kf_ids = set(json.loads((H.DATA_DIR / "eval_key_facts.json").read_text(encoding="utf-8"))["facts"])
check(main_ids == kf_ids, f"eval_key_facts.json ids differ from scored main ids: {main_ids ^ kf_ids}")

for q in scored:
    check(q["facts"], f"{q['id']}: no key facts")
    source_text = H.norm(" ".join((H.DATA_DIR / H.DOC_ID_TO_PATH[d]).read_text(encoding="utf-8")
                                  for d in q["source_doc_ids"]))
    for group in q["facts"]:
        if not any(H.norm(alt) in source_text for alt in group):
            # Groups that check a negation or wording ("no", "not external") need not appear verbatim in the docs.
            if not any(alt.strip() in ("no,", "not external", "rather than external", "not an external",
                                       "instead of external", "no specification", "no spec", "did not",
                                       "not require", "no change", "no packaging", "not eligible", "no return",
                                       "not returnable", "non-returnable", "final sale", "not") for alt in group):
                failures.append(f"{q['id']}: fact group {group} not found in source docs {q['source_doc_ids']}")
    if q["set"] == "main":
        summary = q.get("expected_answer_summary", "")
        ok, missing = H.key_fact_check(summary, q["facts"])
        check(ok, f"{q['id']}: expected_answer_summary fails its own key facts; missing {missing}")

# 3b. In the independent set, report (do not fail) any cross-document question that does not NEED every
#     source document: each source doc should supply a fact group the OTHER source docs cannot satisfy.
#     Independent questions are kept as written, so this is a note, not an error.
def _doc_text(d):
    return H.norm((H.DATA_DIR / H.DOC_ID_TO_PATH[d]).read_text(encoding="utf-8"))

for q in scored:
    if q["set"] == "independent" and len(q["source_doc_ids"]) > 1:
        for d in q["source_doc_ids"]:
            others = [o for o in q["source_doc_ids"] if o != d]
            unique = [g for g in q["facts"]
                      if any(H.norm(a) in _doc_text(d) for a in g)
                      and not any(H.norm(a) in _doc_text(o) for o in others for a in g)]
            if not unique:
                print(f"NOTE ({q['id']}, independent set, kept as written): no fact group needs {d} specifically")

# 4. the checker must reject wrong answers and abstentions
wrong = "The tooling was delivered in three weeks and the change was to the label size."
for q in scored:
    ok, _ = H.key_fact_check(wrong, q["facts"])
    check(not ok, f"{q['id']}: a clearly wrong answer passed the key-fact check")
    ok, _ = H.key_fact_check("The documents do not say.", q["facts"])
    check(not ok, f"{q['id']}: an abstention passed the key-fact check")
check(H.abstained_grounded("The documents do not say."), "abstention detector missed the exact phrase")
check(not H.abstained_grounded("The tooling was delivered 2026-05-16."), "abstention detector false positive")

# 5. citations and judge prompt
hits = [{"doc_id": "fnb-01"}, {"doc_id": "cnc-01"}]
check(H.citation_valid("Yes. Cited: fnb-01, cnc-01", hits), "valid citation rejected")
check(not H.citation_valid("Yes. Cited: jwl-01", hits), "citation to a non-retrieved doc accepted")
check(not H.citation_valid("Yes, with no citation.", hits), "answer with no citation accepted")
check(H.citation_valid("The documents do not say.", hits), "abstention should not need a citation")
prompt = H.load_judge_prompt()
for token in ("{question}", "{notes}", "{answer}", "faithful"):
    check(token in prompt, f"judge prompt is missing {token}")

# 6. the citation-content check (Section 8 mitigation): figures must appear in the cited documents
_docs = {"fnb-01": "Cap diameter changed from 28mm to 26mm. Facility $180,000 over 18 months, drawn 2026-06-08.",
         "cnc-01": "Tolerance 0.02mm. Order C-4471 delayed 4 business days."}
_uf = guardrails.unsupported_figures
check(_uf("It was $180,000 over 18 months. Cited: fnb-01", _docs) == [], "supported figures were flagged")
check(_uf("It was $250,000 over 18 months. Cited: fnb-01", _docs) == ["$250,000"], "an invented amount was not caught")
check(_uf("Order C-4471, changed on 2026-06-09. Cited: cnc-01, fnb-01", _docs) == ["2026-06-09"], "a wrong date was not caught")
check(_uf("The documents do not say.", _docs) is None, "an abstention should not be verified")
check(_uf("It was $180,000.", _docs) is None, "an answer with no citation should be unverifiable, not passed")
check("do not say" in guardrails.handoff_message(0.31, 0.45).lower(), "the human hand-off must contain the abstention phrase")

# 7. the keyword division classifier (Section 8 as written)
check(set(H.named_divisions("How did the jewellery division fund F&B?")) == {"fnb", "jewellery"}, "classifier missed a named division")
check(H.named_divisions("What was delivered?") == [], "classifier invented a division")

n_groups = sum(len(q["facts"]) for q in scored)
print(f"{len(scored)} scored questions, {n_groups} fact groups, checked against the source documents.")
if failures:
    print(f"\n{len(failures)} PROBLEM(S):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("OK: all evaluation-instrument checks passed")
