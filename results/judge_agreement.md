# Judge spot-check: the judge against hand labels

Graded by hand: 10 of 10 sampled answers. Raw agreement: 10/10 (100%). Cohen's kappa: 1.00.

Agreement alone flatters a judge on a set where most answers are fine, so what matters is whether it catches the bad ones. Positive class = **unfaithful**. The sample puts the judge's fails first on purpose (up to 4), so kappa and precision describe this sample, not the whole run; with 10 answers, one disagreement moves kappa a lot.

| | person says unfaithful | person says faithful |
|---|---|---|
| **judge says unfaithful** | 3 (caught) | 0 (false alarm) |
| **judge says faithful** | 0 (**missed**) | 7 |

Precision 100%: it flagged 3, and 3 of those were genuinely unfaithful.
Recall 100%: 3 answers were genuinely unfaithful, and it caught 3.

| id | judge says faithful | I say faithful | judge's reason | my reason |
|---|---|---|---|---|
| CD2 | False | False | The citation fnb-03 is not provided in the NOTES. | cites fnb-03, which is not provided in the notes |
| CD11 | False | False | The citation jwl-03 is not provided in the NOTES, making the claim about it unsupported. | cites jwl-03, which is not provided in the notes |
| S4 | False | False | The answer cites a document that does not exist in the provided notes. | cites cnc-04, which is not provided in the notes |
| S9 | True | True | - | - |
| S5 | True | True | All claims are directly supported by the provided notes. | - |
| S8 | True | True | - | - |
| S2 | True | True | - | - |
| CD6 | True | True | All information in the answer is directly supported by the provided notes. | - |
| PA2 | True | True | - | - |
| CD7 | True | True | - | - |
