"""Evaluation harness for Tanya.

Layers, cheapest first:
  1. Retrieval (no model): did the retrieved chunks cover every division and document a
     question needs?  -> context recall, with a diagnosis of every miss.
  2. Code checks on the answer (no model): key facts present (eval_key_facts.json),
     abstention on out-of-scope questions, over-abstention, citation validity.
  3. Model judge (different model family from the generator): faithfulness to the notes.
     Prompt is read from docs/JUDGE_PROMPT.md. Spot-checked by hand.

Reuses webapp/rag_core.py for chunking, embedding, retrieval and generation so the
numbers describe the same pipeline the app runs. Reads only the FIXED corpus in data/
(never data/uploads/), so uploads cannot move the evaluation.
"""
import json
import random
import re
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webapp"))

import rag_core  # noqa: E402
from check_my_data import DOC_ID_TO_DIVISION, DOC_ID_TO_PATH  # noqa: E402

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
GEN_MODEL_DEFAULT = "openai/gpt-4o-mini"
JUDGE_MODEL_DEFAULT = "google/gemini-2.5-flash"

CONFIGS = {
    "naive_k3": {"kind": "naive", "k": 3, "label": "top-3 by similarity (the notebook default)"},
    "naive_k5": {"kind": "naive", "k": 5, "label": "top-5 by similarity"},
    "titled_k5": {"kind": "naive", "k": 5, "titled": True,
                  "label": "top-5, document title prepended to each chunk before embedding"},
    "parent_d3": {"kind": "parent", "k": 5, "docs": 3,
                  "label": "top-5 chunks, then send their 3 best WHOLE documents"},
    "tfidf_k5": {"kind": "tfidf", "k": 5, "label": "keyword (TF-IDF) top-5: the non-AI baseline"},
    "named_div_k5": {"kind": "named", "k": 5,
                     "label": "keyword division classifier first, then top-5 inside the named divisions (Section 8 as written)"},
    "balanced_2x3": {"kind": "balanced", "per_division": 2,
                     "label": "top-2 from EACH division (6 chunks); division recall 100% by construction"},
    "full_context": {"kind": "full",
                     "label": "all 18 documents in every prompt, no retrieval; recall 100% by construction"},
}
DEFAULT_RAG_CONFIGS = ["naive_k3", "naive_k5", "titled_k5", "parent_d3", "tfidf_k5", "full_context"]

BASELINE_SYSTEM = "Answer in one or two short sentences."
GENERIC_DECLINE = ["do not say", "don't have", "do not have", "cannot", "can't", "unable",
                   "no information", "not aware", "not available", "i'm sorry", "i am sorry"]


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_questions(include_extra=True, include_independent=True):
    """Main 23 (eval_questions.json + eval_key_facts.json), plus optional near-miss and
    independently-authored sets. Every question gets: id, kind, question,
    expected_divisions, source_doc_ids, facts (list of groups), why, set."""
    key_facts = _load_json(ROOT / "eval_key_facts.json")["facts"]
    out = []
    for q in _load_json(ROOT / "eval_questions.json")["questions"]:
        item = dict(q)
        item["set"] = "main"
        if q["kind"] == "out_of_scope":
            item["facts"] = []
            item["why"] = "The corpus does not contain the answer; the right behaviour is to abstain."
        else:
            item["facts"] = key_facts[q["id"]]["groups"]
            item["why"] = key_facts[q["id"]]["why"]
        out.append(item)

    for name, path, flag in (("extra", ROOT / "eval" / "extra_questions.json", include_extra),
                             ("breaker", ROOT / "eval" / "breaker_questions.json", include_extra),
                             ("independent", ROOT / "eval" / "independent_questions.json", include_independent)):
        if flag and path.exists():
            for q in _load_json(path)["questions"]:
                item = dict(q)
                item["set"] = name
                item["facts"] = q.get("groups", [])
                item.setdefault("why", "")
                item.setdefault("source_doc_ids", [])
                if "kind" not in item:
                    item["kind"] = "cross_division" if len(q["expected_divisions"]) > 1 else "single_division"
                out.append(item)
    return out


# ---------------------------------------------------------------------------
# Index and retrieval configs
# ---------------------------------------------------------------------------

def build_index(titled=False, embedder=None, chunk_words=None, overlap=None):
    """One index over the FIXED corpus. titled=True prepends each document's title to every
    chunk before embedding; the text sent to the model is unchanged."""
    chunks, docs = [], {}
    for doc_id, rel in DOC_ID_TO_PATH.items():
        text = (DATA_DIR / rel).read_text(encoding="utf-8")
        docs[doc_id] = text
        title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), doc_id)
        size = chunk_words or rag_core.CHUNK_WORDS
        ov = rag_core.OVERLAP if overlap is None else overlap
        for c in rag_core.chunk(text, size, ov):
            chunks.append({"text": c, "doc_id": doc_id, "division": DOC_ID_TO_DIVISION[doc_id], "title": title})
    texts = [c["text"] for c in chunks]
    embed_texts = [f"{c['title']}. {c['text']}" for c in chunks] if titled else texts
    embedder = embedder or rag_core.Embedder(texts)
    return {"chunks": chunks, "docs": docs, "matrix": embedder.embed(embed_texts), "embedder": embedder}


def build_indexes():
    """Everything the configs need: plain embeddings, title-prefixed embeddings, and a keyword
    (TF-IDF) index for the non-AI baseline. The embedding model is loaded once and shared."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    plain = build_index()
    titled = build_index(titled=True, embedder=plain["embedder"])
    vec = TfidfVectorizer().fit([c["text"] for c in plain["chunks"]])
    m = vec.transform([c["text"] for c in plain["chunks"]]).toarray()
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return {"plain": plain, "titled": titled, "tfidf": {"vectorizer": vec, "matrix": m / np.where(norms == 0, 1, norms)}}


DIVISION_KEYWORDS = {"fnb": ["f&b", "fnb", "food", "beverage"], "cnc": ["cnc", "machin"], "jewellery": ["jewel", "gold"]}


def named_divisions(question):
    """Rule-based query classifier: which divisions does the question name? (Problem statement, Section 8:
    'the query is classified by division with a keyword matching or a quick LLM check'.)"""
    t = question.lower()
    return [d for d, ks in DIVISION_KEYWORDS.items() if any(k in t for k in ks)]


def _scores_and_chunks(config, question, idx):
    spec = CONFIGS[config]
    if spec["kind"] == "named":
        chunks, scores = idx["plain"]["chunks"], idx["plain"]["matrix"] @ idx["plain"]["embedder"].embed([question])[0]
        divs = named_divisions(question)
        if divs:
            scores = scores + np.array([0.0 if c["division"] in divs else -np.inf for c in chunks])
        return chunks, scores
    if spec["kind"] == "tfidf":
        t = idx["tfidf"]
        q = t["vectorizer"].transform([question]).toarray()[0]
        n = np.linalg.norm(q)
        return idx["plain"]["chunks"], t["matrix"] @ (q / n if n else q)
    base = idx["titled"] if spec.get("titled") else idx["plain"]
    return base["chunks"], base["matrix"] @ base["embedder"].embed([question])[0]


def retrieve_config(config, question, idx):
    spec = CONFIGS[config]
    kind = spec["kind"]
    plain = idx["plain"]
    if kind == "full":
        return [{"text": t, "doc_id": d, "division": DOC_ID_TO_DIVISION[d], "score": 1.0}
                for d, t in plain["docs"].items()]
    if kind == "balanced":
        args = (question, plain["chunks"], plain["matrix"], plain["embedder"])
        hits = []
        for division in rag_core.DIVISIONS:
            hits += rag_core.retrieve(*args, k=spec["per_division"], divisions=[division])
        return sorted(hits, key=lambda h: -h["score"])
    chunks, scores = _scores_and_chunks(config, question, idx)
    order = np.argsort(-scores)[:spec["k"]]
    hits = [{**chunks[i], "score": float(scores[i])} for i in order]
    if kind == "parent":
        best = {}
        for h in hits:
            best.setdefault(h["doc_id"], h["score"])
        return [{"text": plain["docs"][d], "doc_id": d, "division": DOC_ID_TO_DIVISION[d], "score": sc}
                for d, sc in list(best.items())[:spec["docs"]]]
    return hits


def _diagnose_missing(q, config, hits, idx):
    """For each expected document that was NOT retrieved: where did its best chunk rank
    among ALL chunks, and what was its score against the cutoff of what was retrieved?"""
    if CONFIGS[config]["kind"] == "full":
        return []
    got_docs = {h["doc_id"] for h in hits}
    chunks, scores = _scores_and_chunks(config, q["question"], idx)
    order = np.argsort(-scores)
    cutoff = min(h["score"] for h in hits)
    diag = []
    for doc_id in q["source_doc_ids"]:
        if doc_id in got_docs:
            continue
        for pos, i in enumerate(order):
            if chunks[i]["doc_id"] == doc_id:
                diag.append({"missing_doc": doc_id, "best_chunk_rank": pos + 1,
                             "best_chunk_score": round(float(scores[i]), 3),
                             "retrieval_cutoff_score": round(float(cutoff), 3)})
                break
    return diag


def recall_for_question(q, config, idx):
    hits = retrieve_config(config, q["question"], idx)
    got_div = {h["division"] for h in hits}
    got_docs = {h["doc_id"] for h in hits}
    need_docs = set(q["source_doc_ids"])
    return {
        "id": q["id"], "kind": q["kind"], "set": q["set"],
        "division_recall": set(q["expected_divisions"]) <= got_div,
        "doc_recall": (len(need_docs & got_docs) / len(need_docs)) if need_docs else None,
        "n_chunks": len(hits),
        "words_sent": sum(len(h["text"].split()) for h in hits),
        "retrieved": [(h["doc_id"], round(h["score"], 3)) for h in hits],
        "diagnosis": _diagnose_missing(q, config, hits, idx) if (need_docs - got_docs) else [],
    }


def summarise_recall(records):
    scored = [r for r in records if r["kind"] != "out_of_scope"]
    cross = [r for r in scored if r["kind"] == "cross_division"]

    def rate(rs, key):
        return (sum(1 for r in rs if r[key]) / len(rs)) if rs else None

    docs = [r["doc_recall"] for r in scored if r["doc_recall"] is not None]
    return {
        "n_scored": len(scored), "n_cross": len(cross),
        "division_recall_cross": rate(cross, "division_recall"),
        "division_recall_all": rate(scored, "division_recall"),
        "avg_doc_recall": (sum(docs) / len(docs)) if docs else None,
        "avg_chunks": (sum(r["n_chunks"] for r in scored) / len(scored)) if scored else None,
        "avg_words": (sum(r["words_sent"] for r in scored) / len(scored)) if scored else None,
    }


# ---------------------------------------------------------------------------
# Code checks on answers (no model)
# ---------------------------------------------------------------------------

def norm(s):
    return (s or "").lower().replace(",", "")


def key_fact_check(answer, facts):
    """Every group needs at least one of its alternatives in the answer."""
    a = norm(answer)
    missing = [g for g in facts if not any(norm(alt) in a for alt in g)]
    return (len(facts) > 0 and not missing), missing


def abstained_grounded(answer):
    return "do not say" in (answer or "").lower()


def declined_generic(answer):
    a = (answer or "").lower()
    return any(p in a for p in GENERIC_DECLINE)


def cited_ids(answer):
    m = re.search(r"cited:\s*(.+)$", answer or "", re.I | re.S)
    return set(re.findall(r"\b[a-z]{3}-\d{2}\b", m.group(1).lower())) if m else set()


def citation_valid(answer, hits):
    """A non-abstaining answer must cite at least one document, and every cited id must
    be one of the documents actually retrieved for that question."""
    if abstained_grounded(answer):
        return True
    ids = cited_ids(answer)
    return bool(ids) and ids <= {h["doc_id"] for h in hits}


def _generate(client, prompt, **kw):
    """rag_core.generate with up to 3 attempts, so one dropped connection or rate-limit
    does not throw away a whole run."""
    last = None
    for attempt in range(3):
        try:
            return rag_core.generate(client, prompt, **kw)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"model call failed after 3 attempts: {last}") from last


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------

def load_judge_prompt():
    return (ROOT / "docs" / "JUDGE_PROMPT.md").read_text(encoding="utf-8").split("```")[1].strip()


def judge_answer(client, q, hits, answer, judge_model):
    notes = "\n".join(f"({h['doc_id']}) {h['text']}" for h in hits)
    prompt = (load_judge_prompt().replace("{question}", q["question"])
              .replace("{notes}", notes).replace("{answer}", answer))
    text, tok = _generate(client, prompt, model=judge_model, max_new_tokens=900)
    obj = rag_core._extract_json_object(text)
    faithful = obj.get("faithful") if isinstance(obj, dict) and isinstance(obj.get("faithful"), bool) else None
    return {
        "judge_faithful": faithful,
        "judge_unsupported": (obj or {}).get("unsupported", ""),
        "judge_why": (obj or {}).get("why", "" if faithful is not None else "judge returned no usable JSON"),
        "judge_tokens": tok,
    }


# ---------------------------------------------------------------------------
# Running the questions
# ---------------------------------------------------------------------------

def run_rag_question(client, q, config, idx, gen_model, judge_model, do_judge, abstain_below=None):
    hits = retrieve_config(config, q["question"], idx)
    handoff = (abstain_below is not None and CONFIGS[config]["kind"] in ("naive", "parent", "balanced", "named")
               and hits and hits[0]["score"] < abstain_below)
    if handoff:
        answer, tok = rag_core.handoff_message(hits[0]["score"], abstain_below), {"in": 0, "out": 0}
    else:
        context = "\n\n".join(f"[{i+1}] ({h['doc_id']}) {h['text']}" for i, h in enumerate(hits))
        answer, tok = _generate(client, f"NOTES:\n{context}\n\nQUESTION: {q['question']}",
                                system=rag_core.GROUNDED, model=gen_model, max_new_tokens=400)
    abst = abstained_grounded(answer)
    rec = {"id": q["id"], "kind": q["kind"], "set": q["set"], "question": q["question"],
           "answer": answer, "abstained": abst, "citation_valid": citation_valid(answer, hits),
           "retrieved": [h["doc_id"] for h in hits], "notes": "\n".join(h["text"] for h in hits),
           "tokens_in": tok["in"], "tokens_out": tok["out"], "handoff": bool(handoff),
           "figures_unsupported": rag_core.unsupported_figures(answer, idx["plain"]["docs"])}
    if q["kind"] == "out_of_scope":
        rec["pass"] = abst
    else:
        ok, missing = key_fact_check(answer, q["facts"])
        rec.update({"key_fact_pass": ok, "missing_facts": missing, "over_abstained": abst})
    if do_judge and not abst:
        rec.update(judge_answer(client, q, hits, answer, judge_model))
    return rec


def run_baseline_question(client, q, gen_model):
    answer, tok = _generate(client, q["question"], system=BASELINE_SYSTEM,
                                    model=gen_model, max_new_tokens=200)
    rec = {"id": q["id"], "kind": q["kind"], "set": q["set"], "question": q["question"],
           "answer": answer, "tokens_in": tok["in"], "tokens_out": tok["out"]}
    if q["kind"] == "out_of_scope":
        rec["pass"] = declined_generic(answer)
    else:
        rec["key_fact_pass"], rec["missing_facts"] = key_fact_check(answer, q["facts"])
    return rec


def aggregate(records):
    scored = [r for r in records if r["kind"] != "out_of_scope"]
    oos = [r for r in records if r["kind"] == "out_of_scope"]
    cross = [r for r in scored if r["kind"] == "cross_division"]
    answered = [r for r in records if "abstained" in r and not r["abstained"]]
    judged = [r for r in records if r.get("judge_faithful") is not None]
    verifiable = [r for r in records if isinstance(r.get("figures_unsupported"), list)]
    rag_records = [r for r in records if "abstained" in r]

    def rate(rs, fn):
        return (sum(1 for r in rs if fn(r)) / len(rs)) if rs else None

    n = len(records) or 1
    return {
        "n": len(records), "n_scored": len(scored), "n_oos": len(oos),
        "key_fact_pass": rate(scored, lambda r: r["key_fact_pass"]),
        "key_fact_pass_cross": rate(cross, lambda r: r["key_fact_pass"]),
        "over_abstain": rate(scored, lambda r: r.get("over_abstained", False)),
        "oos_correct": rate(oos, lambda r: r["pass"]),
        "citation_valid": rate(answered, lambda r: r["citation_valid"]),
        "judge_faithful": rate(judged, lambda r: r["judge_faithful"]),
        "judge_n": len(judged),
        "figures_supported": rate(verifiable, lambda r: not r["figures_unsupported"]),
        "figures_n": len(verifiable),
        "handoff": rate(rag_records, lambda r: r.get("handoff", False)),
        "avg_tokens_in": sum(r["tokens_in"] for r in records) / n,
        "avg_tokens_out": sum(r["tokens_out"] for r in records) / n,
        "judge_tokens_in": sum(r.get("judge_tokens", {}).get("in", 0) for r in records),
        "judge_tokens_out": sum(r.get("judge_tokens", {}).get("out", 0) for r in records),
    }


# ---------------------------------------------------------------------------
# Judge spot-check (human agreement)
# ---------------------------------------------------------------------------

def make_spotcheck(records, out_dir, n=6, seed=7):
    """Sample judged answers (every judge FAIL first, up to 2, then random passes) for you
    to grade by hand. Fill in human_faithful (true/false) then run --agreement."""
    judged = [r for r in records if r.get("judge_faithful") is not None]
    fails = [r for r in judged if r["judge_faithful"] is False][:2]
    passes = [r for r in judged if r["judge_faithful"] is True]
    random.Random(seed).shuffle(passes)
    items = [{"id": r["id"], "question": r["question"], "notes": r["notes"], "answer": r["answer"],
              "judge_faithful": r["judge_faithful"], "judge_why": r.get("judge_why", ""),
              "human_faithful": None} for r in (fails + passes)[:n]]
    (out_dir / "judge_spotcheck.json").write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return items


def agreement(out_dir=RESULTS_DIR):
    path = out_dir / "judge_spotcheck.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    graded = [i for i in items if isinstance(i.get("human_faithful"), bool)]
    if not graded:
        return None
    agree = sum(1 for i in graded if i["human_faithful"] == i["judge_faithful"])
    lines = [f"# Judge spot-check: human vs judge", "",
             f"Graded by hand: {len(graded)} of {len(items)} sampled answers. "
             f"Agreement: {agree}/{len(graded)} ({agree/len(graded):.0%}).", "",
             "| id | judge | you | judge's reason |", "|---|---|---|---|"]
    for i in graded:
        lines.append(f"| {i['id']} | {i['judge_faithful']} | {i['human_faithful']} | {i['judge_why']} |")
    (out_dir / "judge_agreement.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return agree, len(graded)


# ---------------------------------------------------------------------------
# Offline stand-in client, for plumbing tests only (never used for reported numbers)
# ---------------------------------------------------------------------------

class FakeClient:
    def __init__(self):
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    @staticmethod
    def _create(model, messages, temperature, max_tokens):
        text = messages[-1]["content"]
        if "Reply with JSON and nothing else" in text:
            out = '{"faithful": true, "unsupported": "", "why": "dry run"}'
        elif "NOTES:" in text and "QUESTION:" in text:
            out = "Dry-run answer. Cited: fnb-01"
        else:
            out = "Dry-run baseline answer."
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=out))],
            usage=types.SimpleNamespace(prompt_tokens=len(text) // 4, completion_tokens=len(out) // 4))


def abstention_curve(questions, idx, config="naive_k5", thresholds=(0.40, 0.45, 0.50, 0.55, 0.60)):
    """How well does the best retrieval score separate questions the corpus answers from ones it does not?
    Free (no model). NOTE: thresholds are judged on the same questions, so treat as optimistic."""
    answerable, absent = [], []
    for q in questions:
        top = retrieve_config(config, q["question"], idx)[0]["score"]
        (absent if q["kind"] == "out_of_scope" else answerable).append(top)
    rows = [{"threshold": t,
             "absent_caught": sum(1 for s_ in absent if s_ < t), "n_absent": len(absent),
             "answerable_lost": sum(1 for s_ in answerable if s_ < t), "n_answerable": len(answerable)}
            for t in thresholds]
    return rows, {"absent": sorted(absent), "answerable_min": min(answerable), "answerable_median": float(np.median(answerable))}


def _strip_leaked(question, leaked_alts):
    """Remove the exact phrases that leaked from the question text, so what is left is the
    ask without the answer in it. Case-insensitive, longest phrase first so that removing
    'best-before' does not leave a fragment of 'best-before date' behind."""
    out = question
    for alt in sorted(leaked_alts, key=len, reverse=True):
        out = re.sub(re.escape(alt), " ", out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()


def leakage_check(questions, idx, config="naive_k5"):
    """Watch-outs section 6: "does the input already contain the answer? Strip it, and report
    the score before and after." Free (no model).

    Two kinds of leakage matter for a retrieval evaluation, and they fail differently:

    1. Question-side leakage. The question already states one of the key facts the answer is
       graded on, so `key_fact_check` can pass on words the asker supplied rather than words
       the system retrieved. Measured by running the SAME check against the question text.
    2. Retrieval-side leakage. The question repeats enough of the source document's wording
       that retrieval becomes string matching. Measured by deleting the leaked phrases and
       re-scoring recall: the before/after gap is how much of the recall those copied words
       were carrying.

    Returns (rows, summary). Only scored (answerable) questions are examined; out-of-scope
    questions have no key facts to leak.
    """
    rows = []
    for q in questions:
        if q["kind"] == "out_of_scope" or not q.get("facts"):
            continue
        qn = norm(q["question"])
        leaked_alts = [alt for g in q["facts"] for alt in g if norm(alt) in qn]
        leaked_groups = [g for g in q["facts"] if any(norm(alt) in qn for alt in g)]

        before = recall_for_question(q, config, idx)
        if leaked_alts:
            stripped = dict(q)
            stripped["question"] = _strip_leaked(q["question"], leaked_alts)
            after = recall_for_question(stripped, config, idx)
        else:
            stripped, after = q, before

        rows.append({
            "id": q["id"], "set": q.get("set", "main"),
            "n_facts": len(q["facts"]), "n_leaked_groups": len(leaked_groups),
            "leaked": sorted({a for a in leaked_alts}),
            "question_stripped": stripped["question"] if leaked_alts else "",
            "division_recall_before": before["division_recall"],
            "division_recall_after": after["division_recall"],
            "doc_recall_before": before["doc_recall"],
            "doc_recall_after": after["doc_recall"],
        })

    leaky = [r for r in rows if r["n_leaked_groups"]]
    def mean(rs, k):
        vals = [r[k] for r in rs if r[k] is not None]
        return (sum(vals) / len(vals)) if vals else None
    summary = {
        "n_questions": len(rows),
        "n_with_leakage": len(leaky),
        "share_with_leakage": (len(leaky) / len(rows)) if rows else None,
        # Averaged over the leaky questions only -- the others are unchanged by construction.
        "doc_recall_before": mean(leaky, "doc_recall_before"),
        "doc_recall_after": mean(leaky, "doc_recall_after"),
        "division_recall_before": mean(leaky, "division_recall_before"),
        "division_recall_after": mean(leaky, "division_recall_after"),
        # Over the whole scored set, so it is comparable with results/retrieval_recall.md.
        "all_doc_recall_before": mean(rows, "doc_recall_before"),
        "all_doc_recall_after": mean(rows, "doc_recall_after"),
    }
    return rows, summary
