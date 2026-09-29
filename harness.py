"""Evaluation harness for Tanya.

Layers, cheapest first:
  1. Retrieval (no model): did the retrieved chunks cover every division and document a
     question needs?  -> context recall, with a diagnosis of every miss.
  2. Code checks on the answer (no model): key facts present (eval_key_facts.json),
     abstention on out-of-scope questions, over-abstention, citation validity.
  3. Model judge (different model family from the generator): faithfulness to the notes.
     Prompt is read from docs/JUDGE_PROMPT.md. Spot-checked by hand.

Reuses rag_core.py for chunking, embedding, retrieval and generation, and guardrails.py for the
code checks, so the numbers describe the same pipeline the app runs. The `shipped` config is
exactly the app (top-5, title-prefixed embedding, human hand-off below config.ABSTAIN_BELOW);
`tfidf_k5` is THE baseline it is measured against: keyword search over the same chunks, a
non-AI method, rather than a model with no retrieval at all (which has never seen these
fictional documents, scores near zero, and so teaches nothing). Reads only the FIXED corpus in
data/ (never data/uploads/), so uploads cannot move the evaluation.
"""
import json
import random
import re
import time
import types
from pathlib import Path

import numpy as np

import config as cfg   # imported as cfg: many functions below take a parameter named `config`
import guardrails
import rag_core
from config import DATA_DIR, DOC_ID_TO_DIVISION, DOC_ID_TO_PATH, RESULTS_DIR, ROOT

GEN_MODEL_DEFAULT = cfg.GEN_MODEL
JUDGE_MODEL_DEFAULT = cfg.JUDGE_MODEL

CONFIGS = {
    "shipped": {"kind": "follow", "k": cfg.TOP_K, "extra": cfg.FOLLOW_REFERENCES, "titled": cfg.TITLED_EMBEDDING,
                "abstain_below": cfg.ABSTAIN_BELOW,
                "label": f"WHAT THE APP SHIPS: top-{cfg.TOP_K}, title-prefixed embedding, then up to "
                         f"{cfg.FOLLOW_REFERENCES} chunks that share a reference id with them; handed to a "
                         f"person below {cfg.ABSTAIN_BELOW}"},
    "previous_shipped": {"kind": "naive", "k": cfg.TOP_K, "titled": True, "abstain_below": cfg.ABSTAIN_BELOW,
                         "label": f"THE PREVIOUS VERSION, before reference-following: top-{cfg.TOP_K}, "
                                  f"title-prefixed embedding, handed to a person below {cfg.ABSTAIN_BELOW}"},
    "naive_k3": {"kind": "naive", "k": 3, "label": "top-3 by similarity (the notebook default)"},
    "naive_k5": {"kind": "naive", "k": 5, "label": "top-5 by similarity"},
    "titled_k5": {"kind": "naive", "k": 5, "titled": True,
                  "label": "top-5, document title prepended to each chunk before embedding"},
    "parent_d3": {"kind": "parent", "k": 5, "docs": 3,
                  "label": "top-5 chunks, then send their 3 best WHOLE documents"},
    "tfidf_k5": {"kind": "tfidf", "k": 5,
                 "label": "THE BASELINE: keyword (TF-IDF) top-5 over the same chunks, non-AI retrieval"},
    "named_div_k5": {"kind": "named", "k": 5,
                     "label": "keyword division classifier first, then top-5 inside the named divisions (the mitigation first proposed)"},
    "balanced_2x3": {"kind": "balanced", "per_division": 2,
                     "label": "top-2 from EACH division (6 chunks); division recall 100% by construction"},
    "full_context": {"kind": "full",
                     "label": "all 18 documents in every prompt, no retrieval; recall 100% by construction"},
    # Retrieval alternatives, measured free and not shipped. Each changes ONE thing.
    "hybrid_k5": {"kind": "hybrid", "k": 5,
                  "label": "EXPERIMENT: hybrid search, the shipped embeddings and the keyword baseline "
                           "fused by reciprocal rank, top-5"},
    "titled_k7": {"kind": "naive", "k": 7, "titled": True, "abstain_below": cfg.ABSTAIN_BELOW,
                  "label": "CONTROL for reference-following: the previous version with the same budget of "
                           "7 chunks, and no following"},
}
SHIPPED = "shipped"
PREVIOUS = "previous_shipped"
BASELINE = "tfidf_k5"
# The live run: the shipped system against THE baseline, the comparison every headline number is about,
# plus the previous version on the same questions, so adopting reference-following is judged on
# answers, not only on retrieval. Any other config is opt-in with --configs.
DEFAULT_RAG_CONFIGS = [SHIPPED, PREVIOUS, BASELINE]
ALTERNATIVE_RAG_CONFIGS = ["naive_k5", "titled_k5", "naive_k3", "parent_d3", "full_context"]
RRF_K = 60   # the usual reciprocal-rank-fusion constant; it damps the influence of rank 1
REFERENCE_ID = rag_core.REFERENCE_ID
follow_references = rag_core.follow_references   # the app's own step: one implementation, not two

BASELINE_SYSTEM = "Answer in one or two short sentences."
# A partially answerable question should get its answerable half AND a plain statement that the rest
# is not in the documents. These phrases are how an answer says so; gap_flagged() records it.
GAP_PHRASES = ["do not say", "does not say", "don't say", "doesn't say", "do not mention", "does not mention",
               "not mentioned", "do not specify", "does not specify", "not specified", "not stated",
               "do not state", "does not state", "not given", "not provided", "not disclosed", "not named",
               "not listed", "not recorded", "no information", "not included", "do not include",
               "does not include", "not available", "not in the notes", "not in the documents", "unknown",
               "no record", "do not provide", "does not provide", "do not indicate", "does not indicate",
               "do not name", "does not name", "not identified", "do not identify", "does not identify",
               "withheld", "not quantified", "not reported", "no figure", "no count"]
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
    key_facts = _load_json(DATA_DIR / "eval_key_facts.json")["facts"]
    out = []
    for q in _load_json(DATA_DIR / "eval_questions.json")["questions"]:
        item = dict(q)
        item["set"] = "main"
        if q["kind"] == "out_of_scope":
            item["facts"] = []
            item["why"] = "The corpus does not contain the answer; the right behaviour is to abstain."
        else:
            item["facts"] = key_facts[q["id"]]["groups"]
            item["why"] = key_facts[q["id"]]["why"]
        out.append(item)

    for name, path, flag in (("extra", DATA_DIR / "extra_questions.json", include_extra),
                             ("breaker", DATA_DIR / "breaker_questions.json", include_extra),
                             ("partial", DATA_DIR / "partial_questions.json", include_extra),
                             ("independent", DATA_DIR / "independent_questions.json", include_independent)):
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
        title = rag_core.doc_title({"text": text, "doc_id": doc_id})
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
    """Rule-based query classifier: which divisions does the question name? (the problem statement's first
    proposed mitigation: 'the query is classified by division with a keyword matching or a quick LLM check'.)"""
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
    if spec["kind"] == "hybrid":
        # Reciprocal rank fusion: each chunk scores 1/(60 + its rank) in each list, summed. Ranks,
        # not raw scores, because cosine and TF-IDF scores live on different scales.
        _, dense = _scores_and_chunks(SHIPPED, question, idx)
        chunks, sparse = _scores_and_chunks(BASELINE, question, idx)
        fused = np.zeros(len(chunks))
        for scores in (dense, sparse):
            ranks = np.empty(len(scores), dtype=int)
            ranks[np.argsort(-scores)] = np.arange(1, len(scores) + 1)
            fused += 1.0 / (RRF_K + ranks)
        return chunks, fused
    # "follow" ranks exactly as the shipped retrieval does; its extra step is in retrieve_config
    base = idx["titled"] if (spec.get("titled") or spec["kind"] == "follow") else idx["plain"]
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
    if kind == "follow":
        return follow_references(hits, chunks, scores, spec["extra"])
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


def reciprocal_rank(hits, need_docs):
    """1 / the position of the first retrieved chunk from a needed document; 0 if none was retrieved.
    Averaged over questions this is MRR (Class 2's retrieval metrics, beside recall@k): recall asks
    WHETHER the evidence arrived, MRR asks how near the top the first of it sits."""
    for pos, h in enumerate(hits, 1):
        if h["doc_id"] in need_docs:
            return 1.0 / pos
    return 0.0


def recall_for_question(q, config, idx):
    hits = retrieve_config(config, q["question"], idx)
    got_div = {h["division"] for h in hits}
    got_docs = {h["doc_id"] for h in hits}
    need_docs = set(q["source_doc_ids"])
    return {
        "id": q["id"], "kind": q["kind"], "set": q["set"],
        "division_recall": set(q["expected_divisions"]) <= got_div,
        "doc_recall": (len(need_docs & got_docs) / len(need_docs)) if need_docs else None,
        # no ranking to speak of when every document is sent in corpus order
        "rr": reciprocal_rank(hits, need_docs) if need_docs and CONFIGS[config]["kind"] != "full" else None,
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
    rrs = [r["rr"] for r in scored if r.get("rr") is not None]
    return {
        "n_scored": len(scored), "n_cross": len(cross),
        "division_recall_cross": rate(cross, "division_recall"),
        "division_recall_all": rate(scored, "division_recall"),
        "avg_doc_recall": (sum(docs) / len(docs)) if docs else None,
        "all_docs_share": (sum(1 for d in docs if d == 1.0) / len(docs)) if docs else None,
        "mrr": (sum(rrs) / len(rrs)) if rrs else None,
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


def gap_flagged(answer):
    """Does the answer say that part of what was asked is not in the documents? For a partially
    answerable question this is the honest behaviour; silence about the missing half is not."""
    body = re.split(r"cited:", answer or "", flags=re.I)[0].lower()
    return any(p in body for p in GAP_PHRASES)


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
    # The shipped config carries the app's own threshold, whatever --abstain-below says: its row
    # must describe the app. Every other config uses the command-line threshold (default: none).
    threshold = CONFIGS[config].get("abstain_below", abstain_below)
    handoff = (threshold is not None and CONFIGS[config]["kind"] in ("naive", "parent", "balanced", "named", "follow")
               and hits and hits[0]["score"] < threshold)
    if handoff:
        answer, tok = guardrails.handoff_message(hits[0]["score"], threshold), {"in": 0, "out": 0}
    else:
        context = rag_core.format_notes(hits)   # the app's own prompt builder, strip included
        answer, tok = _generate(client, f"NOTES:\n{context}\n\nQUESTION: {q['question']}",
                                system=rag_core.GROUNDED, model=gen_model, max_new_tokens=400)
    abst = abstained_grounded(answer)
    rec = {"id": q["id"], "kind": q["kind"], "set": q["set"], "question": q["question"],
           "answer": answer, "abstained": abst, "citation_valid": citation_valid(answer, hits),
           "retrieved": [h["doc_id"] for h in hits],
           "notes": "\n\n".join(f"({h['doc_id']}) {h['text']}" for h in hits),   # as the judge sees them
           "tokens_in": tok["in"], "tokens_out": tok["out"], "handoff": bool(handoff),
           # Were ALL the documents this question needs in front of the model? The evidence side of
           # "should it have declined?" (see aggregate), and the detector for the silent failure:
           # answering anyway when they were not.
           "evidence_retrieved": (set(q["source_doc_ids"]) <= {h["doc_id"] for h in hits}
                                  if q["kind"] != "out_of_scope" and q.get("source_doc_ids") else None),
           "figures_unsupported": guardrails.unsupported_figures(answer, idx["plain"]["docs"])}
    if q["kind"] == "out_of_scope":
        rec["pass"] = abst
    else:
        ok, missing = key_fact_check(answer, q["facts"])
        rec.update({"key_fact_pass": ok, "missing_facts": missing, "over_abstained": abst})
        if q["kind"] == "partially_answerable":
            rec["gap_flagged"] = (not abst) and gap_flagged(answer)
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

    # Abstention as the TWO numbers the course watch-outs ask for: how often it declines,
    # and whether the questions it declined were ones it would have got wrong. "Would have got
    # wrong" is judged on evidence, not guessed: a decline is RIGHT when the question is out of
    # scope, or when retrieval did not put every document the question needs in front of the
    # model (so any answer would have been unsupported). It is WRONG when the evidence was all
    # there. Declines where the needed documents are not recorded (some added sets) are left out.
    declines = [r for r in rag_records if r["abstained"]]
    judgeable = [r for r in declines if r["kind"] == "out_of_scope" or r.get("evidence_retrieved") is not None]
    # The silent failure: it ANSWERED an answerable question although the documents
    # that question needs were not retrieved -- the shape of every confident hallucination found.
    answered_scored = [r for r in scored if "abstained" in r and not r["abstained"]
                       and r.get("evidence_retrieved") is not None]

    n = len(records) or 1
    return {
        "declined": rate(rag_records, lambda r: r["abstained"]),
        "n_declined": len(declines),
        "declines_right": rate(judgeable, lambda r: r["kind"] == "out_of_scope"
                               or r.get("evidence_retrieved") is False),
        "declines_judged": len(judgeable),
        "answered_without_evidence": rate(answered_scored, lambda r: r["evidence_retrieved"] is False),
        "answered_without_evidence_n": sum(1 for r in answered_scored if r["evidence_retrieved"] is False),
        "answered_without_evidence_wrong": sum(1 for r in answered_scored
                                               if r["evidence_retrieved"] is False and not r["key_fact_pass"]),
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
        # partially answerable set: of the answers that did not decline outright, how many said
        # the rest of the question is not in the documents
        "gap_flagged": rate([r for r in records if "gap_flagged" in r and not r["abstained"]],
                            lambda r: r["gap_flagged"]),
        "avg_tokens_in": sum(r["tokens_in"] for r in records) / n,
        "avg_tokens_out": sum(r["tokens_out"] for r in records) / n,
        "judge_tokens_in": sum(r.get("judge_tokens", {}).get("in", 0) for r in records),
        "judge_tokens_out": sum(r.get("judge_tokens", {}).get("out", 0) for r in records),
    }


# ---------------------------------------------------------------------------
# Judge spot-check (human agreement)
# ---------------------------------------------------------------------------

def make_spotcheck(records, out_dir, n=10, max_fails=4, seed=7):
    """Sample judged answers for you to grade by hand: the judge's FAILs first (up to max_fails, so
    precision can be measured at all), then random passes (so recall can: a missed unfaithful answer
    hides among the passes). Writes results/judge_spotcheck.json, where you set human_faithful to
    true/false, and results/judge_spotcheck_to_grade.md, the same items laid out for reading.
    Grade from the notes and the answer alone, before looking at the judge's verdict."""
    judged = [r for r in records if r.get("judge_faithful") is not None]
    fails = [r for r in judged if r["judge_faithful"] is False][:max_fails]
    passes = [r for r in judged if r["judge_faithful"] is True]
    random.Random(seed).shuffle(passes)
    items = [{"id": r["id"], "question": r["question"], "notes": r["notes"], "answer": r["answer"],
              "judge_faithful": r["judge_faithful"], "judge_why": r.get("judge_why", ""),
              "human_faithful": None} for r in (fails + passes)[:n]]
    (out_dir / "judge_spotcheck.json").write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    write_spotcheck_md(items, out_dir)
    return items


def _labelled_notes(notes):
    """Split "(doc_id) text" notes and head each with its document id and title, numbering the parts
    when one document arrives as two overlapping chunks, so a grader can tell what came from where."""
    titles = {d: rag_core.doc_title({"text": (DATA_DIR / p).read_text(encoding="utf-8"), "doc_id": d})
              for d, p in DOC_ID_TO_PATH.items()}
    blocks = []
    for block in notes.split("\n\n"):
        m = re.match(r"\((\S+?)\) (.*)", block, re.S)
        blocks.append((m.group(1), m.group(2)) if m else ("?", block))
    total = {d: sum(1 for b, _ in blocks if b == d) for d, _ in blocks}
    seen, out = {}, []
    for k, (doc, text) in enumerate(blocks, 1):
        seen[doc] = seen.get(doc, 0) + 1
        part = f", part {seen[doc]} of {total[doc]}" if total[doc] > 1 else ""
        # a chunk that starts at its document's "# Title" line would render as one giant heading
        text = re.sub(r"^\s*#", r"\\#", text)
        out += [f"**Note {k}: {doc} · {titles.get(doc, doc)}{part}**", "", "> " + text, ""]
    return out


def write_spotcheck_md(items, out_dir):
    """The spot-check laid out for reading: question, answer, then every note headed by its document."""
    L = ["# Judge spot-check: grade these by hand (temporary file)", "",
         "For each item, read the answer, then check each of its claims against the notes below it. "
         "**Yes** = every claim is supported by the notes. **No** = at least one claim is not (say which). "
         "Being right about the world does not count: only what the notes say. Decide before you open "
         "the judge's verdict at the end of the item.", "",
         "Tip: the answer's `Cited:` line names the documents it used; start with those notes.", "",
         "Reply in one line, for example: `1 yes, 2 no (invents a date), 3 yes, ...`", ""]
    for k, i in enumerate(items, 1):
        L += [f"## {k}. {i['id']}", "", f"**Question:** {i['question']}", "", f"**Answer:** {i['answer']}", "",
              "### Notes the model was given", ""] + _labelled_notes(i["notes"]) + [
              f"<details><summary>The judge's verdict (open after grading)</summary>{i['judge_faithful']}: "
              f"{i['judge_why']}</details>", "", "---", ""]
    (out_dir / "judge_spotcheck_to_grade.md").write_text("\n".join(L), encoding="utf-8")


def cohens_kappa(pairs):
    """Cohen's kappa for two raters' true/false labels: agreement corrected for the agreement two
    raters would reach by chance given how often each says true (Class 2: align the judge to people
    and track kappa, not raw agreement, which flatters a judge on a set where most answers pass).
    None when chance agreement is total (both raters gave one label only), where kappa is undefined."""
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pa, pb = sum(1 for a, _ in pairs if a) / n, sum(1 for _, b in pairs if b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def agreement(out_dir=RESULTS_DIR):
    """Compare the judge against hand labels. The course watch-outs: a judge is a
    component of the system, not a source of truth, so it needs precision and recall against
    labels a person assigned -- not just an agreement percentage, which flatters any judge on
    a set where most answers are fine.

    The judge exists to CATCH unfaithful answers, so "unfaithful" is the positive class:
      precision = of the answers the judge flagged, how many a person agreed were unfaithful
      recall    = of the answers a person called unfaithful, how many the judge flagged
    A judge that never flags anything scores 0 recall here, however high its agreement.
    """
    path = out_dir / "judge_spotcheck.json"
    if not path.exists():      # the spot-check files are temporary: deleted once the grades are recorded
        return None
    items = json.loads(path.read_text(encoding="utf-8"))
    graded = [i for i in items if isinstance(i.get("human_faithful"), bool)]
    if not graded:
        return None
    agree = sum(1 for i in graded if i["human_faithful"] == i["judge_faithful"])

    # positive class = UNFAITHFUL (judge_faithful is False)
    tp = sum(1 for i in graded if not i["judge_faithful"] and not i["human_faithful"])
    fp = sum(1 for i in graded if not i["judge_faithful"] and i["human_faithful"])
    fn = sum(1 for i in graded if i["judge_faithful"] and not i["human_faithful"])
    tn = sum(1 for i in graded if i["judge_faithful"] and i["human_faithful"])
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    kappa = cohens_kappa([(i["judge_faithful"], i["human_faithful"]) for i in graded])

    def pct(x):
        return "n/a" if x is None else f"{x:.0%}"

    lines = ["# Judge spot-check: the judge against hand labels", "",
             f"Graded by hand: {len(graded)} of {len(items)} sampled answers. "
             f"Raw agreement: {agree}/{len(graded)} ({agree/len(graded):.0%}). "
             f"Cohen's kappa: {'undefined (one label only)' if kappa is None else f'{kappa:.2f}'}.", "",
             "Agreement alone flatters a judge on a set where most answers are fine, so what "
             "matters is whether it catches the bad ones. Positive class = **unfaithful**. The sample "
             "puts the judge's fails first on purpose (up to 4), so kappa and precision describe this "
             "sample, not the whole run; with 10 answers, one disagreement moves kappa a lot.", "",
             "| | person says unfaithful | person says faithful |", "|---|---|---|",
             f"| **judge says unfaithful** | {tp} (caught) | {fp} (false alarm) |",
             f"| **judge says faithful** | {fn} (**missed**) | {tn} |", "",
             f"Precision {pct(prec)}: it flagged {tp + fp}, and {tp} of those were genuinely unfaithful.",
             f"Recall {pct(rec)}: {tp + fn} answers were genuinely unfaithful, and it caught {tp}.", ""]
    if (tp + fn) == 0:
        lines += ["Caveat: no answer in this sample was judged unfaithful by hand, so recall is "
                  "undefined and this sample says nothing about what the judge misses. Grade more "
                  "answers, weighted towards ones you suspect, before trusting it.", ""]
    lines += ["| id | judge says faithful | I say faithful | judge's reason | my reason |", "|---|---|---|---|---|"]
    for i in graded:
        lines.append(f"| {i['id']} | {i['judge_faithful']} | {i['human_faithful']} | {i['judge_why'] or '-'} | "
                     f"{i.get('human_note') or '-'} |")
    (out_dir / "judge_agreement.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return agree, len(graded), kappa


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


def abstention_curve(questions, idx, config=SHIPPED, thresholds=(0.40, 0.45, 0.50, 0.55, 0.60)):
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


def leakage_check(questions, idx, config=SHIPPED):
    """The course watch-outs: "does the input already contain the answer? Strip it, and report
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
