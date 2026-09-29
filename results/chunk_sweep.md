# Chunk-size sweep (no model, no cost)

Embedder: local embeddings (all-MiniLM-L6-v2) -- matches MEANING. Fixed corpus, 37 answerable questions from every set; cross-division column uses the main set's 11 cross-division questions. The problem statement's smallest slice used 25 words with 10 overlap; the notebook and app now use 200 with 50.

| chunk / overlap | chunks | top-k | cross-division recall | avg doc recall | avg words sent |
|---|---|---|---|---|---|
| 25 / 10 | 212 | 3 | 36% | 75% | 74 |
| 25 / 10 | 212 | 5 | 55% | 82% | 124 |
| 40 / 10 | 109 | 3 | 36% | 73% | 117 |
| 40 / 10 | 109 | 5 | 73% | 83% | 194 |
| 60 / 15 | 74 | 3 | 73% | 77% | 173 |
| 60 / 15 | 74 | 5 | 82% | 86% | 286 |
| 100 / 25 | 48 | 3 | 27% | 77% | 275 |
| 100 / 25 | 48 | 5 | 55% | 87% | 452 |
| 150 / 40 | 33 | 3 | 45% | 83% | 367 |
| 150 / 40 | 33 | 5 | 73% | 92% | 596 |
| 200 / 50 | 21 | 3 | 64% | 84% | 488 |
| 200 / 50 | 21 | 5 | 91% | 90% | 823 |
| 250 / 60 | 19 | 3 | 64% | 84% | 531 |
| 250 / 60 | 19 | 5 | 91% | 91% | 890 |
| 300 / 75 | 18 | 3 | 64% | 84% | 546 |
| 300 / 75 | 18 | 5 | 91% | 94% | 931 |
