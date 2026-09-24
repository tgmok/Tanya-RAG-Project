# Real-world validation slice — jewellery retail transactions

**Source:** "eCommerce purchase history from jewelry store" (Michael Kechinov / REES46),
`kaggle.com/datasets/mkechinov/ecommerce-purchase-history-from-jewelry-store`.
95,911 real transactions from an actual online jewellery retailer, Dec 2018 - Feb 2019.
Downloaded by the user directly from Kaggle (this dataset has no public mirror and
requires a Kaggle account) on 2026-09-14.
**Licence:** Published by the dataset author for open research/analysis use on Kaggle.

**This file is NOT part of Tanya's main corpus** -- same reasoning as
`nyc_inspections.md` and `cnc_industrial_safety.md`.

**This slice is a different shape than the other two.** It's real transaction data
(category, price, metal, gem, colour), not narrative document text -- there are no
sentences to chunk and retrieve the way there are in the F&B/CNC slices. It validates
**pricing plausibility**: does the synthetic quote logic in
`jewellery/gold_pricing_policy.md` and `jewellery/client_quote_template.md` land in a
realistic real-world range? It does not validate whether TGMOK Holdings' jewellery SOPs
read like real internal documents -- there is no equivalent real text for that
(see `README_validation.md`).

---

## Real transaction sample (8 rows, one per category + 2 extra for metal/gem variety)

| id | date | category | metal | gem | colour | price (USD) |
|---|---|---|---|---|---|---|
| jwl-real-01 | 2018-12-01 | earring | gold | diamond | red | 561.51 |
| jwl-real-02 | 2018-12-03 | ring | gold | diamond | white | 180.71 |
| jwl-real-03 | 2018-12-02 | pendant | gold | diamond | red | 88.90 |
| jwl-real-04 | 2018-12-17 | bracelet | gold | diamond | red | 588.90 |
| jwl-real-05 | 2019-01-25 | necklace | gold | diamond | red | 321.78 |
| jwl-real-06 | 2019-02-20 | brooch | gold | diamond | red | 458.77 |
| jwl-real-07 | 2019-01-23 | ring | gold | sapphire | red | 287.53 |
| jwl-real-08 | 2018-12-05 | pendant | silver | fianit | (unlabelled) | 1.03 |

## Real market price distribution, gold items with a stated gem (full dataset, n=60,566)

| category | count | mean (USD) | median (USD) | min | max |
|---|---|---|---|---|---|
| earring | 23,889 | 435.96 | 313.70 | 30.00 | 34,448.60 |
| ring | 21,889 | 407.19 | 321.78 | 20.71 | 26,424.52 |
| pendant | 9,110 | 195.51 | 136.85 | 13.56 | 7,513.56 |
| bracelet | 3,333 | 555.83 | 295.75 | 53.38 | 4,202.74 |
| necklace | 1,817 | 384.53 | 321.78 | 58.77 | 3,482.16 |
| brooch | 528 | 483.59 | 347.19 | 27.67 | 3,088.90 |

## Validation point worth writing up

TGMOK Holdings' example quote (`jewellery/client_quote_template.md`, job JWL-Q-3391) is
an **18-karat gold, 12g, custom-engraved pendant requiring a new stamping die**, totalling
**$2,029.92**. The real median gold+diamond pendant price above is **$136.85** -- an
order of magnitude lower. This is not necessarily a flaw: the real distribution mixes
mass-market and bespoke pieces, and TGMOK's quote is explicitly a custom commission with
a one-time die-tooling charge ($850 of the $2,029.92), which a median off-the-shelf
pendant wouldn't carry. But it's worth stating plainly rather than silently: the
synthetic quote sits near the high end of the real pendant price range (max $7,513.56),
not at the median, and that should be named as a limitation of the synthetic example
rather than assumed to be typical.
