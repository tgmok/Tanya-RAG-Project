# Judge spot-check: the judge against hand labels

Graded by hand: 10 of 10 sampled answers. Raw agreement: 10/10 (100%). Cohen's kappa: 1.00.

Agreement alone flatters a judge on a set where most answers are fine, so what matters is whether it catches the bad ones. Positive class = **unfaithful**. The sample puts the judge's fails first on purpose (up to 4), so kappa and precision describe this sample, not the whole run; with 10 answers, one disagreement moves kappa a lot.

| | person says unfaithful | person says faithful |
|---|---|---|
| **judge says unfaithful** | 2 (caught) | 0 (false alarm) |
| **judge says faithful** | 0 (**missed**) | 8 |

Precision 100%: it flagged 2, and 2 of those were genuinely unfaithful.
Recall 100%: 2 answers were genuinely unfaithful, and it caught 2.

| id | judge says faithful | I say faithful | judge's reason | my reason |
|---|---|---|---|---|
| CD1 | False | False | The answer cites a document (cnc-05) that is not provided in the NOTES. | cites cnc-05, which was not provided in the notes |
| S4 | False | False | The notes state a tolerance of ±0.02mm on thread pitch and ±0.05mm on head diameter, not a single ±0.02mm tolerance for the entire work order. | states a single +/-0.02 mm tolerance, but the tooling spec gives +/-0.02 mm for thread pitch and +/-0.05 mm for head diameter |
| CD11 | True | True | - | - |
| PA2 | True | True | All claims are directly supported by the provided notes. | - |
| PA4 | True | True | - | - |
| IND4 | True | True | - | - |
| CD7 | True | True | - | - |
| S2 | True | True | - | - |
| CD8 | True | True | - | - |
| S8 | True | True | - | - |
