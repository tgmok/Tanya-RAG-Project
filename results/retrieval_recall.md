# Retrieval recall by configuration (no model, no cost)

Embedder: local embeddings (all-MiniLM-L6-v2) -- matches MEANING. Chunking: 200 words, overlap 50. Fixed corpus only (18 documents, 21 chunks).

`shipped` is exactly what the app runs. `tfidf_k5` is THE baseline: keyword search over the same chunks, a non-AI method, so the comparison asks whether embeddings earn their complexity.

Division recall = the retrieved chunks cover EVERY division the question needs (the context-recall metric). Doc recall = share of the needed documents retrieved. Target for cross-division division recall: 80%.

Caveat: `balanced_2x3` and `full_context` cover every division by construction, so their division recall is 100% by design and shows nothing about choosing the right documents. Compare avg doc recall, words sent, and the answer-level results from --run, instead.

MRR = mean reciprocal rank of the first chunk from a needed document (1.0 = always first). Misses count every scored question in every set that is missing at least one needed document.

| config | cross-division recall (main 11) | all scored (main 20) | avg doc recall (main 20) | MRR (main 20) | misses (all scored) | avg items sent | avg words sent |
|---|---|---|---|---|---|---|---|
| `shipped`: WHAT THE APP SHIPS: top-5, title-prefixed embedding, then up to 2 chunks that share a reference id with them; handed to a person below 0.45 | 100% | 100% | 98% | 0.92 | 1/37 | 6.9 | 1188 |
| `previous_shipped`: THE PREVIOUS VERSION, before reference-following: top-5, title-prefixed embedding, handed to a person below 0.45 | 100% | 100% | 88% | 0.92 | 5/37 | 5.0 | 837 |
| `naive_k3`: top-3 by similarity (the notebook default) | 64% | 80% | 78% | 0.92 | 10/37 | 3.0 | 492 |
| `naive_k5`: top-5 by similarity | 91% | 95% | 88% | 0.93 | 7/37 | 5.0 | 826 |
| `titled_k5`: top-5, document title prepended to each chunk before embedding | 100% | 100% | 88% | 0.92 | 5/37 | 5.0 | 837 |
| `parent_d3`: top-5 chunks, then send their 3 best WHOLE documents | 64% | 80% | 78% | 0.92 | 10/37 | 3.0 | 576 |
| `tfidf_k5`: THE BASELINE: keyword (TF-IDF) top-5 over the same chunks, non-AI retrieval | 91% | 95% | 91% | 0.89 | 5/37 | 5.0 | 865 |
| `named_div_k5`: keyword division classifier first, then top-5 inside the named divisions (the mitigation first proposed) | 45% | 70% | 81% | 0.94 | 10/37 | 5.0 | 835 |
| `balanced_2x3`: top-2 from EACH division (6 chunks); division recall 100% by construction | 100% | 100% | 88% | 0.92 | 5/37 | 6.0 | 1004 |
| `full_context`: all 18 documents in every prompt, no retrieval; recall 100% by construction | 100% | 100% | 100% | n/a | 0/37 | 18.0 | 3228 |
| `hybrid_k5`: EXPERIMENT: hybrid search, the shipped embeddings and the keyword baseline fused by reciprocal rank, top-5 | 100% | 100% | 93% | 0.90 | 3/37 | 5.0 | 853 |
| `hybrid_follow`: EXPERIMENT: hybrid search, then the shipped reference-following step: does hybrid add anything on top of what ships? | 100% | 100% | 98% | 0.90 | 1/37 | 7.0 | 1204 |
| `titled_k7`: CONTROL for reference-following: the previous version with the same budget of 7 chunks, and no following | 100% | 100% | 93% | 0.92 | 3/37 | 7.0 | 1154 |

## Reference-following, adopted, and the alternatives

Each row changes one thing from `previous_shipped`, the retrieval before reference-following.

- **`shipped`** adds a fixed code step: follow the reference ids the retrieved notes mention. Document recall 88% -> 98%, questions missing a needed document 5 -> 1 of 37, words sent 837 -> 1188. Its effect on the answers is in `results/summary.md`.
- **`titled_k7`**, its control: the same 7-chunk budget with no following: document recall 93%, misses 3 of 37, words 1154. What `shipped` gains over this row is the reference-following itself, not the two extra chunks.
- **`hybrid_k5`** (embeddings and keyword search fused by rank, Class 2's hybrid search): document recall 93%, misses 3 of 37, words 853. Better than the retrieval before reference-following, on its own.
- **`hybrid_follow`**, hybrid search with the shipped reference-following step on top: document recall 98%, misses 1 of 37, words 1204, against 98% and 1 for `shipped`. It adds nothing on top of what ships, so hybrid search is not adopted.

Caveat: the synthetic documents were written with shared reference ids across each cross-division hook, which flatters reference-following. Real documents cite each other less consistently.


## Misses under `shipped` (1 questions missing at least one needed document)

- **CD12** (cross_division, main); retrieved [('cnc-04', 0.537), ('jwl-01', 0.425), ('cnc-03', 0.413), ('cnc-02', 0.412), ('fnb-01', 0.41), ('cnc-01', 0.41), ('cnc-06', 0.403)]
  - `jwl-02`: best chunk ranked #20 of 21 at score 0.22, versus a retrieval cutoff of 0.403

## Misses under `previous_shipped` (5 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.66), ('fnb-01', 0.603), ('cnc-04', 0.502), ('cnc-02', 0.492), ('cnc-06', 0.477)]
  - `cnc-01`: best chunk ranked #8 of 21 at score 0.432, versus a retrieval cutoff of 0.477
- **CD2** (cross_division, main); retrieved [('fnb-01', 0.581), ('cnc-02', 0.545), ('fnb-04', 0.506), ('fnb-01', 0.485), ('fnb-02', 0.466)]
  - `cnc-01`: best chunk ranked #7 of 21 at score 0.433, versus a retrieval cutoff of 0.466
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.514), ('fnb-01', 0.502), ('cnc-02', 0.479), ('jwl-06', 0.464), ('jwl-05', 0.447)]
  - `cnc-01`: best chunk ranked #12 of 21 at score 0.345, versus a retrieval cutoff of 0.447
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.537), ('jwl-01', 0.425), ('cnc-03', 0.413), ('cnc-02', 0.412), ('fnb-01', 0.41)]
  - `cnc-06`: best chunk ranked #7 of 21 at score 0.403, versus a retrieval cutoff of 0.41
  - `jwl-02`: best chunk ranked #20 of 21 at score 0.22, versus a retrieval cutoff of 0.41
- **PA4** (partially_answerable, partial); retrieved [('jwl-06', 0.556), ('jwl-04', 0.535), ('cnc-04', 0.497), ('jwl-05', 0.468), ('cnc-02', 0.464)]
  - `cnc-06`: best chunk ranked #6 of 21 at score 0.454, versus a retrieval cutoff of 0.464

## Misses under `naive_k3` (10 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.653), ('fnb-01', 0.568), ('cnc-02', 0.494)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.494
- **CD2** (cross_division, main); retrieved [('fnb-01', 0.584), ('cnc-02', 0.551), ('fnb-04', 0.513)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.513
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.52), ('fnb-01', 0.515), ('jwl-06', 0.493)]
  - `cnc-01`: best chunk ranked #11 of 21 at score 0.378, versus a retrieval cutoff of 0.493
- **CD4** (cross_division, main); retrieved [('cnc-02', 0.593), ('cnc-06', 0.486), ('fnb-01', 0.434)]
  - `fnb-02`: best chunk ranked #6 of 21 at score 0.33, versus a retrieval cutoff of 0.434
- **CD8** (cross_division, main); retrieved [('fnb-06', 0.628), ('fnb-04', 0.439), ('fnb-02', 0.415)]
  - `jwl-01`: best chunk ranked #4 of 21 at score 0.393, versus a retrieval cutoff of 0.415
- **CD9** (cross_division, main); retrieved [('cnc-04', 0.399), ('cnc-02', 0.332), ('fnb-01', 0.31)]
  - `jwl-01`: best chunk ranked #5 of 21 at score 0.257, versus a retrieval cutoff of 0.31
- **CD11** (cross_division, main); retrieved [('jwl-06', 0.628), ('jwl-02', 0.547), ('jwl-04', 0.53)]
  - `cnc-04`: best chunk ranked #4 of 21 at score 0.495, versus a retrieval cutoff of 0.53
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.535), ('cnc-01', 0.443), ('fnb-01', 0.437)]
  - `cnc-06`: best chunk ranked #5 of 21 at score 0.416, versus a retrieval cutoff of 0.437
  - `jwl-02`: best chunk ranked #16 of 21 at score 0.26, versus a retrieval cutoff of 0.437
- **PA1** (partially_answerable, partial); retrieved [('cnc-02', 0.68), ('fnb-02', 0.576), ('fnb-01', 0.465)]
  - `cnc-06`: best chunk ranked #6 of 21 at score 0.441, versus a retrieval cutoff of 0.465
- **PA4** (partially_answerable, partial); retrieved [('jwl-06', 0.565), ('jwl-04', 0.558), ('cnc-02', 0.471)]
  - `cnc-06`: best chunk ranked #7 of 21 at score 0.45, versus a retrieval cutoff of 0.471

## Misses under `naive_k5` (7 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.653), ('fnb-01', 0.568), ('cnc-02', 0.494), ('cnc-04', 0.485), ('cnc-06', 0.476)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.476
- **CD2** (cross_division, main); retrieved [('fnb-01', 0.584), ('cnc-02', 0.551), ('fnb-04', 0.513), ('fnb-01', 0.501), ('fnb-02', 0.479)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.479
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.52), ('fnb-01', 0.515), ('jwl-06', 0.493), ('jwl-02', 0.48), ('cnc-02', 0.472)]
  - `cnc-01`: best chunk ranked #11 of 21 at score 0.378, versus a retrieval cutoff of 0.472
- **CD4** (cross_division, main); retrieved [('cnc-02', 0.593), ('cnc-06', 0.486), ('fnb-01', 0.434), ('cnc-04', 0.418), ('cnc-05', 0.38)]
  - `fnb-02`: best chunk ranked #6 of 21 at score 0.33, versus a retrieval cutoff of 0.38
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.535), ('cnc-01', 0.443), ('fnb-01', 0.437), ('cnc-03', 0.418), ('cnc-06', 0.416)]
  - `jwl-02`: best chunk ranked #16 of 21 at score 0.26, versus a retrieval cutoff of 0.416
- **PA1** (partially_answerable, partial); retrieved [('cnc-02', 0.68), ('fnb-02', 0.576), ('fnb-01', 0.465), ('fnb-04', 0.459), ('jwl-01', 0.447)]
  - `cnc-06`: best chunk ranked #6 of 21 at score 0.441, versus a retrieval cutoff of 0.447
- **PA4** (partially_answerable, partial); retrieved [('jwl-06', 0.565), ('jwl-04', 0.558), ('cnc-02', 0.471), ('cnc-04', 0.467), ('jwl-05', 0.455)]
  - `cnc-06`: best chunk ranked #7 of 21 at score 0.45, versus a retrieval cutoff of 0.455

## Misses under `titled_k5` (5 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.66), ('fnb-01', 0.603), ('cnc-04', 0.502), ('cnc-02', 0.492), ('cnc-06', 0.477)]
  - `cnc-01`: best chunk ranked #8 of 21 at score 0.432, versus a retrieval cutoff of 0.477
- **CD2** (cross_division, main); retrieved [('fnb-01', 0.581), ('cnc-02', 0.545), ('fnb-04', 0.506), ('fnb-01', 0.485), ('fnb-02', 0.466)]
  - `cnc-01`: best chunk ranked #7 of 21 at score 0.433, versus a retrieval cutoff of 0.466
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.514), ('fnb-01', 0.502), ('cnc-02', 0.479), ('jwl-06', 0.464), ('jwl-05', 0.447)]
  - `cnc-01`: best chunk ranked #12 of 21 at score 0.345, versus a retrieval cutoff of 0.447
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.537), ('jwl-01', 0.425), ('cnc-03', 0.413), ('cnc-02', 0.412), ('fnb-01', 0.41)]
  - `cnc-06`: best chunk ranked #7 of 21 at score 0.403, versus a retrieval cutoff of 0.41
  - `jwl-02`: best chunk ranked #20 of 21 at score 0.22, versus a retrieval cutoff of 0.41
- **PA4** (partially_answerable, partial); retrieved [('jwl-06', 0.556), ('jwl-04', 0.535), ('cnc-04', 0.497), ('jwl-05', 0.468), ('cnc-02', 0.464)]
  - `cnc-06`: best chunk ranked #6 of 21 at score 0.454, versus a retrieval cutoff of 0.464

## Misses under `parent_d3` (10 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.653), ('cnc-02', 0.494), ('cnc-04', 0.485)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.485
- **CD2** (cross_division, main); retrieved [('fnb-01', 0.584), ('cnc-02', 0.551), ('fnb-04', 0.513)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.513
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.52), ('fnb-01', 0.515), ('jwl-06', 0.493)]
  - `cnc-01`: best chunk ranked #11 of 21 at score 0.378, versus a retrieval cutoff of 0.493
- **CD4** (cross_division, main); retrieved [('cnc-02', 0.593), ('cnc-06', 0.486), ('fnb-01', 0.434)]
  - `fnb-02`: best chunk ranked #6 of 21 at score 0.33, versus a retrieval cutoff of 0.434
- **CD8** (cross_division, main); retrieved [('fnb-06', 0.628), ('fnb-04', 0.439), ('fnb-02', 0.415)]
  - `jwl-01`: best chunk ranked #4 of 21 at score 0.393, versus a retrieval cutoff of 0.415
- **CD9** (cross_division, main); retrieved [('cnc-04', 0.399), ('cnc-02', 0.332), ('fnb-01', 0.31)]
  - `jwl-01`: best chunk ranked #5 of 21 at score 0.257, versus a retrieval cutoff of 0.31
- **CD11** (cross_division, main); retrieved [('jwl-06', 0.628), ('jwl-02', 0.547), ('jwl-04', 0.53)]
  - `cnc-04`: best chunk ranked #4 of 21 at score 0.495, versus a retrieval cutoff of 0.53
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.535), ('cnc-01', 0.443), ('fnb-01', 0.437)]
  - `cnc-06`: best chunk ranked #5 of 21 at score 0.416, versus a retrieval cutoff of 0.437
  - `jwl-02`: best chunk ranked #16 of 21 at score 0.26, versus a retrieval cutoff of 0.437
- **PA1** (partially_answerable, partial); retrieved [('cnc-02', 0.68), ('fnb-02', 0.576), ('fnb-01', 0.465)]
  - `cnc-06`: best chunk ranked #6 of 21 at score 0.441, versus a retrieval cutoff of 0.465
- **PA4** (partially_answerable, partial); retrieved [('jwl-06', 0.565), ('jwl-04', 0.558), ('cnc-02', 0.471)]
  - `cnc-06`: best chunk ranked #7 of 21 at score 0.45, versus a retrieval cutoff of 0.471

## Misses under `tfidf_k5` (5 questions missing at least one needed document)

- **CD3** (cross_division, main); retrieved [('fnb-01', 0.277), ('fnb-01', 0.171), ('cnc-02', 0.167), ('cnc-01', 0.127), ('fnb-03', 0.117)]
  - `cnc-04`: best chunk ranked #8 of 21 at score 0.091, versus a retrieval cutoff of 0.117
- **CD8** (cross_division, main); retrieved [('fnb-04', 0.116), ('fnb-06', 0.108), ('cnc-01', 0.1), ('fnb-02', 0.095), ('jwl-02', 0.083)]
  - `jwl-01`: best chunk ranked #7 of 21 at score 0.065, versus a retrieval cutoff of 0.083
- **CD11** (cross_division, main); retrieved [('jwl-02', 0.215), ('jwl-06', 0.214), ('jwl-05', 0.187), ('jwl-04', 0.149), ('jwl-01', 0.147)]
  - `cnc-04`: best chunk ranked #8 of 21 at score 0.136, versus a retrieval cutoff of 0.147
- **CD12** (cross_division, main); retrieved [('jwl-04', 0.212), ('fnb-01', 0.208), ('jwl-01', 0.183), ('cnc-06', 0.16), ('jwl-05', 0.157)]
  - `jwl-02`: best chunk ranked #9 of 21 at score 0.138, versus a retrieval cutoff of 0.157
- **NM2** (near_miss, extra); retrieved [('cnc-02', 0.309), ('cnc-01', 0.245), ('fnb-06', 0.217), ('cnc-06', 0.206), ('fnb-02', 0.191)]
  - `jwl-01`: best chunk ranked #7 of 21 at score 0.165, versus a retrieval cutoff of 0.191

## Misses under `named_div_k5` (10 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.653), ('fnb-01', 0.568), ('cnc-02', 0.494), ('cnc-04', 0.485), ('cnc-06', 0.476)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.476
- **CD2** (cross_division, main); retrieved [('cnc-02', 0.551), ('cnc-01', 0.466), ('cnc-04', 0.369), ('cnc-06', 0.339), ('cnc-03', 0.321)]
  - `fnb-04`: best chunk ranked #15 of 21 at score -inf, versus a retrieval cutoff of 0.321
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.52), ('fnb-01', 0.515), ('jwl-06', 0.493), ('jwl-02', 0.48), ('cnc-02', 0.472)]
  - `cnc-01`: best chunk ranked #11 of 21 at score 0.378, versus a retrieval cutoff of 0.472
- **CD4** (cross_division, main); retrieved [('cnc-02', 0.593), ('cnc-06', 0.486), ('cnc-04', 0.418), ('cnc-05', 0.38), ('cnc-03', 0.273)]
  - `fnb-02`: best chunk ranked #17 of 21 at score -inf, versus a retrieval cutoff of 0.273
- **CD5** (cross_division, main); retrieved [('cnc-02', 0.51), ('cnc-01', 0.483), ('cnc-06', 0.453), ('cnc-03', 0.415), ('cnc-04', 0.361)]
  - `fnb-04`: best chunk ranked #15 of 21 at score -inf, versus a retrieval cutoff of 0.361
- **CD8** (cross_division, main); retrieved [('fnb-06', 0.628), ('fnb-04', 0.439), ('fnb-02', 0.415), ('fnb-01', 0.366), ('fnb-02', 0.353)]
  - `jwl-01`: best chunk ranked #12 of 21 at score -inf, versus a retrieval cutoff of 0.353
- **CD9** (cross_division, main); retrieved [('cnc-04', 0.399), ('cnc-02', 0.332), ('cnc-06', 0.246), ('cnc-03', 0.211), ('cnc-05', 0.201)]
  - `jwl-01`: best chunk ranked #10 of 21 at score -inf, versus a retrieval cutoff of 0.201
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.535), ('cnc-01', 0.443), ('cnc-03', 0.418), ('cnc-06', 0.416), ('cnc-02', 0.405)]
  - `jwl-02`: best chunk ranked #12 of 21 at score 0.26, versus a retrieval cutoff of 0.405
- **NM2** (near_miss, extra); retrieved [('fnb-06', 0.645), ('fnb-02', 0.389), ('fnb-04', 0.371), ('fnb-01', 0.314), ('fnb-02', 0.288)]
  - `jwl-01`: best chunk ranked #12 of 21 at score -inf, versus a retrieval cutoff of 0.288
- **PA4** (partially_answerable, partial); retrieved [('jwl-06', 0.565), ('jwl-04', 0.558), ('cnc-02', 0.471), ('cnc-04', 0.467), ('jwl-05', 0.455)]
  - `cnc-06`: best chunk ranked #7 of 21 at score 0.45, versus a retrieval cutoff of 0.455

## Misses under `balanced_2x3` (5 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.653), ('fnb-01', 0.568), ('cnc-02', 0.494), ('cnc-04', 0.485), ('jwl-01', 0.358), ('jwl-06', 0.311)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.466, versus a retrieval cutoff of 0.311
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.52), ('fnb-01', 0.515), ('jwl-06', 0.493), ('jwl-02', 0.48), ('cnc-02', 0.472), ('fnb-02', 0.46)]
  - `cnc-01`: best chunk ranked #11 of 21 at score 0.378, versus a retrieval cutoff of 0.46
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.535), ('cnc-01', 0.443), ('fnb-01', 0.437), ('fnb-01', 0.39), ('jwl-01', 0.384), ('jwl-04', 0.379)]
  - `cnc-06`: best chunk ranked #5 of 21 at score 0.416, versus a retrieval cutoff of 0.379
  - `jwl-02`: best chunk ranked #16 of 21 at score 0.26, versus a retrieval cutoff of 0.379
- **S4** (single_division, main); retrieved [('cnc-03', 0.759), ('cnc-05', 0.532), ('fnb-01', 0.462), ('fnb-01', 0.458), ('jwl-04', 0.345), ('jwl-06', 0.288)]
  - `cnc-01`: best chunk ranked #3 of 21 at score 0.479, versus a retrieval cutoff of 0.288
- **PA4** (partially_answerable, partial); retrieved [('jwl-06', 0.565), ('jwl-04', 0.558), ('cnc-02', 0.471), ('cnc-04', 0.467), ('fnb-01', 0.394), ('fnb-01', 0.381)]
  - `cnc-06`: best chunk ranked #7 of 21 at score 0.45, versus a retrieval cutoff of 0.381

## Misses under `full_context` (0 questions missing at least one needed document)

None.

## Misses under `hybrid_k5` (3 questions missing at least one needed document)

- **CD2** (cross_division, main); retrieved [('fnb-01', 0.032), ('fnb-01', 0.032), ('cnc-02', 0.031), ('fnb-02', 0.031), ('fnb-04', 0.031)]
  - `cnc-01`: best chunk ranked #6 of 21 at score 0.031, versus a retrieval cutoff of 0.031
- **CD3** (cross_division, main); retrieved [('fnb-01', 0.033), ('cnc-02', 0.032), ('cnc-04', 0.031), ('fnb-01', 0.031), ('fnb-02', 0.03)]
  - `cnc-01`: best chunk ranked #7 of 21 at score 0.03, versus a retrieval cutoff of 0.03
- **CD12** (cross_division, main); retrieved [('jwl-01', 0.032), ('fnb-01', 0.032), ('jwl-04', 0.031), ('cnc-06', 0.031), ('cnc-02', 0.03)]
  - `jwl-02`: best chunk ranked #16 of 21 at score 0.027, versus a retrieval cutoff of 0.03

## Misses under `hybrid_follow` (1 questions missing at least one needed document)

- **CD12** (cross_division, main); retrieved [('jwl-01', 0.032), ('fnb-01', 0.032), ('jwl-04', 0.031), ('cnc-06', 0.031), ('cnc-02', 0.03), ('cnc-01', 0.029), ('fnb-04', 0.027)]
  - `jwl-02`: best chunk ranked #16 of 21 at score 0.027, versus a retrieval cutoff of 0.027

## Misses under `titled_k7` (3 questions missing at least one needed document)

- **CD1** (cross_division, main); retrieved [('fnb-01', 0.66), ('fnb-01', 0.603), ('cnc-04', 0.502), ('cnc-02', 0.492), ('cnc-06', 0.477), ('fnb-04', 0.457), ('cnc-03', 0.447)]
  - `cnc-01`: best chunk ranked #8 of 21 at score 0.432, versus a retrieval cutoff of 0.447
- **CD3** (cross_division, main); retrieved [('cnc-04', 0.514), ('fnb-01', 0.502), ('cnc-02', 0.479), ('jwl-06', 0.464), ('jwl-05', 0.447), ('jwl-02', 0.444), ('fnb-02', 0.423)]
  - `cnc-01`: best chunk ranked #12 of 21 at score 0.345, versus a retrieval cutoff of 0.423
- **CD12** (cross_division, main); retrieved [('cnc-04', 0.537), ('jwl-01', 0.425), ('cnc-03', 0.413), ('cnc-02', 0.412), ('fnb-01', 0.41), ('cnc-01', 0.41), ('cnc-06', 0.403)]
  - `jwl-02`: best chunk ranked #20 of 21 at score 0.22, versus a retrieval cutoff of 0.403

## Abstain below a retrieval score? (the confidence threshold; free, no model)

Best retrieval score under `shipped` -- the scores the app's threshold actually sees. Answerable questions: minimum 0.371, median 0.595. Questions the corpus cannot answer: 0.347, 0.389, 0.464, 0.586, 0.622, 0.625.

| abstain below | unanswerable caught | answerable wrongly refused |
|---|---|---|
| 0.40 | 2/6 | 1/37 |
| 0.45 | 2/6 | 1/37 |
| 0.50 | 3/6 | 2/37 |
| 0.55 | 3/6 | 12/37 |
| 0.60 | 4/6 | 19/37 |

Reading it: the unanswerable questions here are deliberately plausible, so their scores overlap the answerable ones. A threshold is a weak backstop, not a substitute for the grounded prompt and the citation check. The thresholds are judged on the same questions they were chosen from, so this is optimistic.

