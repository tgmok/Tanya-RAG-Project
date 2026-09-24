# Chunk-size sweep (no model, no cost)

Embedder: local embeddings (all-MiniLM-L6-v2) -- matches MEANING. Fixed corpus, 31 answerable questions from every set; cross-division column uses the main set's 11 cross-division questions. The problem statement's smallest slice used 25 words with 10 overlap; the notebook and app now use 200 with 50.

| chunk / overlap | chunks | top-k | cross-division recall | avg doc recall | avg words sent |
|---|---|---|---|---|---|
| 25 / 10 | 212 | 3 | 36% | 72% | 74 |
| 25 / 10 | 212 | 5 | 55% | 80% | 124 |
| 40 / 10 | 109 | 3 | 36% | 70% | 117 |
| 40 / 10 | 109 | 5 | 73% | 81% | 194 |
| 60 / 15 | 74 | 3 | 73% | 75% | 174 |
| 60 / 15 | 74 | 5 | 82% | 84% | 286 |
| 100 / 25 | 48 | 3 | 27% | 77% | 274 |
| 100 / 25 | 48 | 5 | 55% | 87% | 456 |
| 150 / 40 | 33 | 3 | 45% | 81% | 367 |
| 150 / 40 | 33 | 5 | 73% | 91% | 592 |
| 200 / 50 | 21 | 3 | 64% | 86% | 491 |
| 200 / 50 | 21 | 5 | 91% | 92% | 821 |
| 250 / 60 | 19 | 3 | 64% | 86% | 530 |
| 250 / 60 | 19 | 5 | 91% | 92% | 889 |
| 300 / 75 | 18 | 3 | 64% | 86% | 549 |
| 300 / 75 | 18 | 5 | 91% | 96% | 934 |
