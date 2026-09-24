"""Run this after every change to data/ or to the corpus manifest in config.py:

    python data/check_my_data.py

Catches broken data before it silently breaks an evaluation run: every registered document
exists, every document on disk is registered, every question points at real documents in the
right divisions, the answer key has the promised shape, and every scored question has
code-checkable key facts. Standard library only.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # config.py lives at the root
from config import DATA_DIR, DIVISIONS, DOC_ID_TO_DIVISION, DOC_ID_TO_PATH  # noqa: E402

# Deliberately separate from the graded corpus: live uploads, the sample upload used by the
# regression demo, and the real-world validation slices.
NON_CORPUS_DIRS = {"uploads", "sample_uploads", "validation_real"}


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
    known_paths = set(DOC_ID_TO_PATH.values())
    for division_dir in DATA_DIR.iterdir():
        if not division_dir.is_dir():
            continue
        if division_dir.name in NON_CORPUS_DIRS:
            continue
        if division_dir.name.startswith(("__", ".")):   # __pycache__, .ipynb_checkpoints: tool
            continue                                    # caches, not data (this file lives in data/)
        if division_dir.name not in set(DIVISIONS):
            ok = fail(f"unexpected directory data/{division_dir.name}") and ok
            continue
        for f in division_dir.glob("*.md"):
            rel = f.relative_to(DATA_DIR).as_posix()
            if rel not in known_paths:
                ok = fail(f"file data/{rel} is not registered in config.DOC_ID_TO_PATH") and ok

    # 3. eval_questions.json must exist and every source_doc_id must resolve.
    eval_path = DATA_DIR / "eval_questions.json"
    if not eval_path.exists():
        return fail("data/eval_questions.json is missing")

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
    facts_path = DATA_DIR / "eval_key_facts.json"
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
