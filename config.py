"""The one place to change Tanya's configuration.

Models, retrieval knobs, guardrail thresholds, prices, cost-model assumptions and the corpus
manifest all live here. Every other module imports from this file, so the app, the notebook
narrative and the evaluation cannot drift onto different settings. Standard library only:
data/check_my_data.py imports it without needing the rest of the stack installed.

Change a value here, then re-run the free checks (README, "Clone to a reproduced run").
"""
from pathlib import Path

# ---- Paths --------------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"      # written by the app only; ignored by git and the evaluation
RESULTS_DIR = ROOT / "results"
DOCS_DIR = ROOT / "docs"
KEY_FILE = ROOT / "OpenRouter_api.txt"  # optional, untracked (.gitignore). Never commit a key.

# ---- Models (OpenRouter) ------------------------------------------------------------------
BASE_URL = "https://openrouter.ai/api/v1"
GEN_MODEL = "openai/gpt-4o-mini"        # answers, classifies uploads, writes impact briefs.
                                        # gpt-5-mini (the problem statement's first choice)
                                        # returned an empty reply in this setup, cause not isolated.
JUDGE_MODEL = "google/gemini-2.5-flash"  # a DIFFERENT model family from the answerer: a model
                                         # grading its own output is grading its own homework.
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # runs locally, no per-call price

# ---- Retrieval ----------------------------------------------------------------------------
# Measured, free, in results/chunk_sweep.md and results/retrieval_recall.md.
CHUNK_WORDS = 200   # cross-division recall 82% -> 91% vs the earlier 60/15, at ~3x the words
OVERLAP = 50        # sent per query (286 -> 823). 200 and 250 tie; 200 is the cheaper of the two.
TOP_K = 5           # top-3 misses a needed division on 36% of cross-division questions; top-5 on 9%.
TITLED_EMBEDDING = True  # prepend each chunk's document title before embedding (what the app
                         # ships): division recall 91% -> 100%, doc recall unchanged at 88%, and
                         # zero extra generation tokens -- only the embedding input changes.

# ---- Guardrails (code, not prompt) --------------------------------------------------------
# A retrieval score below this hands the question to a person with no model call. A backstop,
# not a guarantee: answerable and plausible-but-absent questions overlap in score
# (results/retrieval_recall.md, abstention table).
ABSTAIN_BELOW = 0.45
# A hard, visible stop on one app session's spend (OWASP LLM06:2026 Unbounded Consumption).
# At gpt-4o-mini prices this is under $0.05 even fully spent; the point is the stop, not the sum.
MAX_SESSION_TOKENS = 100_000
ABSTAIN_PHRASE = "The documents do not say."

# ---- Prices, US$ per 1M tokens. Dated. VERIFY at openrouter.ai/models before quoting. -------
PRICES_DATED = "2026-09-21"
PRICES = {
    "openai/gpt-4o-mini": {"in": 0.15, "out": 0.60, "source": "A1 Part 1 notebook (OpenRouter list price)"},
    "google/gemini-2.5-flash": {"in": 0.30, "out": 2.50, "source": "ASSUMPTION: list price as recalled; verify"},
}

# ---- Cost-model ASSUMPTIONS, not measurements. Every one changes the answer. ---------------
HUMAN_REVIEW_MINUTES = 15      # an analyst redoing one wrong/declined answer by hand -- which is also
                               # the no-AI alternative: answering the question from the documents
CHECK_MINUTES = 3              # a person reading EVERY answer against its cited notes before using it
                               # (the human-in-the-loop gate; paid on right answers too)
ANALYST_USD_PER_HOUR = 40.0    # placeholder rate
# Layer 3, fixed monthly: paid whatever the volume, so it gets cheaper per question as volume grows.
FIXED_MONTHLY_USD = {
    "hosting: one small cloud VM for the Streamlit app": 20.0,
    "upkeep: 4 hours a month re-running the free checks and updating documents": 160.0,
    "re-running the answer-level evaluation after each change, about 4 a month": 1.0,
}
MANUAL_CYCLE_DAYS = 4          # midpoint of "3-5 business days" in the problem statement
HOURS_PER_DAY = 8
CYCLES_PER_MONTH = 4.33        # weekly reports
VOLUMES = [200, 2000]          # questions per month
# Answer correctness measured in the final notebook run (results/notebook_run.md, the same 20
# questions). The free cost estimate uses these; `python cost_model.py` after a live run uses
# results/summary.json instead.
NOTEBOOK_CORRECTNESS = {"shipped": 0.80, "tfidf_k5": 0.75}
EST_ANSWER_TOKENS = 90         # output length used by the no-key cost ESTIMATE only; the live run
                               # replaces it with measured completion tokens
CHARS_PER_TOKEN = 4            # the estimate's prompt-token rule of thumb; live runs use API usage

# ---- The graded corpus: 18 documents, 6 per division ---------------------------------------
# Adding a document: put the file under data/<division>/, register it here, then run
#   python data/check_my_data.py
DIVISIONS = ["fnb", "cnc", "jewellery"]
DOC_ID_TO_PATH = {
    "fnb-01": "fnb/fnb-01_packaging_change_sop.md",
    "fnb-02": "fnb/fnb-02_client_contract_summary.md",
    "fnb-03": "fnb/fnb-03_quality_control_checklist.md",
    "fnb-04": "fnb/fnb-04_maintenance_log.md",
    "fnb-05": "fnb/fnb-05_hygiene_sop.md",
    "fnb-06": "fnb/fnb-06_financial_summary_q3.md",
    "cnc-01": "cnc/cnc-01_tooling_spec_bottle_cap.md",
    "cnc-02": "cnc/cnc-02_capacity_planning_report.md",
    "cnc-03": "cnc/cnc-03_machine_calibration_log.md",
    "cnc-04": "cnc/cnc-04_material_procurement_policy.md",
    "cnc-05": "cnc/cnc-05_safety_sop.md",
    "cnc-06": "cnc/cnc-06_client_order_backlog.md",
    "jwl-01": "jewellery/jwl-01_finance_intercompany_loan_report.md",
    "jwl-02": "jewellery/jwl-02_gold_pricing_policy.md",
    "jwl-03": "jewellery/jwl-03_inventory_audit_sop.md",
    "jwl-04": "jewellery/jwl-04_quality_certification_sop.md",
    "jwl-05": "jewellery/jwl-05_retail_returns_policy.md",
    "jwl-06": "jewellery/jwl-06_client_quote_template.md",
}
DOC_ID_TO_DIVISION = {
    doc_id: {"fnb": "fnb", "cnc": "cnc", "jwl": "jewellery"}[doc_id.split("-")[0]]
    for doc_id in DOC_ID_TO_PATH
}
PATH_TO_DOC_ID = {path: doc_id for doc_id, path in DOC_ID_TO_PATH.items()}
