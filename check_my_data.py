"""Run this after every change to data/ or eval_questions.json.

Catches broken data before it silently breaks an eval run. Standard library only.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DIVISIONS = {"fnb", "cnc", "jewellery"}
# Deliberately separate from the graded corpus: live uploads and the real-world validation slices.
NON_CORPUS_DIRS = {"uploads", "validation_real"}

DOC_ID_TO_PATH = {
    "fnb-01": "fnb/packaging_change_sop.md",
    "fnb-02": "fnb/client_contract_summary.md",
    "fnb-03": "fnb/quality_control_checklist.md",
    "fnb-04": "fnb/maintenance_log.md",
    "fnb-05": "fnb/hygiene_sop.md",
    "fnb-06": "fnb/financial_summary_q3.md",
    "cnc-01": "cnc/tooling_spec_bottle_cap.md",
    "cnc-02": "cnc/capacity_planning_report.md",
    "cnc-03": "cnc/machine_calibration_log.md",
    "cnc-04": "cnc/material_procurement_policy.md",
    "cnc-05": "cnc/safety_sop.md",
    "cnc-06": "cnc/client_order_backlog.md",
    "jwl-01": "jewellery/finance_intercompany_loan_report.md",
    "jwl-02": "jewellery/gold_pricing_policy.md",
    "jwl-03": "jewellery/inventory_audit_sop.md",
    "jwl-04": "jewellery/quality_certification_sop.md",
    "jwl-05": "jewellery/retail_returns_policy.md",
    "jwl-06": "jewellery/client_quote_template.md",
}

DOC_ID_TO_DIVISION = {doc_id: doc_id.split("-")[0] for doc_id in DOC_ID_TO_PATH}
DOC_ID_TO_DIVISION = {
    doc_id: {"fnb": "fnb", "cnc": "cnc", "jwl": "jewellery"}[doc_id.split("-")[0]]
    for doc_id in DOC_ID_TO_PATH
}


def fail(msg):
    print(f"FAIL: {msg}")
    return False


def main():
    ok = True

    # 1. Every doc id in the dictionary must exist on disk.
    for doc_id, rel_path in DOC_ID_TO_PATH.items():
        if not (DATA_DIR / rel_path).exists():
            ok = fail(f"{doc_id} points at missing file data/{rel_path}") and ok

    # 2. Every file on disk must be a known doc id (catches orphaned/renamed files).
    known_paths = {str(Path(p)) for p in DOC_ID_TO_PATH.values()}
    for division_dir in DATA_DIR.iterdir():
        if not division_dir.is_dir():
            continue
        if division_dir.name in NON_CORPUS_DIRS:
            continue
        if division_dir.name not in DIVISIONS:
            ok = fail(f"unexpected directory data/{division_dir.name}") and ok
            continue
        for f in division_dir.glob("*.md"):
            rel = str(f.relative_to(DATA_DIR))
            if rel not in known_paths:
                ok = fail(f"file data/{rel} is not registered in DOC_ID_TO_PATH") and ok

    # 3. eval_questions.json must exist and every source_doc_id must resolve.
    eval_path = ROOT / "eval_questions.json"
    if not eval_path.exists():
        return fail("eval_questions.json is missing")

    evalset = json.loads(eval_path.read_text(encoding="utf-8"))
    questions = evalset["questions"]
    seen_ids = set()

    for q in questions:
        qid = q["id"]
        if qid in seen_ids:
            ok = fail(f"duplicate question id {qid}") and ok
        seen_ids.add(qid)

        for doc_id in q.get("source_doc_ids", []):
            if doc_id not in DOC_ID_TO_PATH:
                ok = fail(f"{qid} references unknown doc id {doc_id}") and ok
                continue
            actual_division = DOC_ID_TO_DIVISION[doc_id]
            if actual_division not in q.get("expected_divisions", []):
                ok = fail(
                    f"{qid} cites {doc_id} ({actual_division}) but "
                    f"expected_divisions is {q.get('expected_divisions')}"
                ) and ok

        if q["kind"] == "out_of_scope" and q.get("source_doc_ids"):
            ok = fail(f"{qid} is out_of_scope but lists source_doc_ids") and ok
        if q["kind"] != "out_of_scope" and not q.get("source_doc_ids"):
            ok = fail(f"{qid} is not out_of_scope but has no source_doc_ids") and ok

    # 4. Counts match what the problem statement promises.
    kinds = [q["kind"] for q in questions]
    n_cross = kinds.count("cross_division")
    n_single = kinds.count("single_division")
    n_oos = kinds.count("out_of_scope")
    print(f"{len(questions)} questions total: {n_cross} cross-division, "
          f"{n_single} single-division, {n_oos} out-of-scope")
    if n_cross + n_single != 20:
        ok = fail(f"expected 20 scored questions, found {n_cross + n_single}") and ok
    if n_oos != 3:
        ok = fail(f"expected 3 out-of-scope questions (one per division), found {n_oos}") and ok
    if n_cross <= n_single:
        ok = fail("cross-division questions should outnumber single-division "
                  "('weighted toward cross-division cases')") and ok

    # 5. Every document id is referenced by at least one question (no dead data).
    referenced = {doc_id for q in questions for doc_id in q.get("source_doc_ids", [])}
    unused = set(DOC_ID_TO_PATH) - referenced
    if unused:
        print(f"WARNING: documents never referenced by any eval question: {sorted(unused)}")

    # 6. Every scored question has code-checkable key facts (eval_key_facts.json), and no orphans.
    facts_path = ROOT / "eval_key_facts.json"
    if facts_path.exists():
        key_facts = json.loads(facts_path.read_text(encoding="utf-8"))["facts"]
        scored_ids = {q["id"] for q in questions if q["kind"] != "out_of_scope"}
        if set(key_facts) != scored_ids:
            ok = fail(f"eval_key_facts.json ids differ from scored ids: {sorted(set(key_facts) ^ scored_ids)}") and ok
        for qid, entry in key_facts.items():
            if not entry.get("groups") or not all(entry["groups"]):
                ok = fail(f"{qid} has empty key-fact groups") and ok
    else:
        print("WARNING: eval_key_facts.json not found (answer-level checks need it)")

    if ok:
        print("OK: all checks passed")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
