"""Reproduce the jewellery real-world validation sample and price-distribution table
in jewellery_retail_transactions.md.

Unlike the F&B/CNC slices, the raw source (jewelry.csv, ~13.6MB, 95,911 rows) is NOT
committed to this repo: it needs your own Kaggle login to download, and per the
course watch-outs' guidance ("if you cannot redistribute the data, plan now for a
repository that runs without it -- ship trained weights, a small sample, and a README
that says exactly this"), only the small hand-picked sample and aggregate summary table
are committed here. Run this script against your own local copy to reproduce them.

Usage:
    python build_jewellery_sample.py path/to/jewelry.csv

Requires pandas (only used here, not in the main notebook's dependencies).
"""
import sys

import pandas as pd

COLUMNS = [
    "event_time", "order_id", "product_id", "quantity", "category_id",
    "category_code", "brand", "price", "user_id", "gender", "color", "metal", "gem",
]

VALID_CATEGORIES = [
    "jewelry.earring", "jewelry.ring", "jewelry.pendant",
    "jewelry.bracelet", "jewelry.necklace", "jewelry.brooch",
]


def load(csv_path):
    return pd.read_csv(csv_path, names=COLUMNS, header=None)


def pick_sample(df):
    gold_with_gem = df[
        df["category_code"].isin(VALID_CATEGORIES)
        & (df["metal"] == "gold")
        & (df["price"] > 0)
        & df["gem"].notna()
    ]

    picked = []
    for cat in VALID_CATEGORIES:
        cat_rows = gold_with_gem[gold_with_gem["category_code"] == cat]
        if cat_rows.empty:
            continue
        diamond_rows = cat_rows[cat_rows["gem"] == "diamond"]
        picked.append(diamond_rows.iloc[0] if not diamond_rows.empty else cat_rows.iloc[0])
    return picked, gold_with_gem


def price_summary(gold_with_gem):
    return gold_with_gem.groupby("category_code")["price"].agg(
        ["count", "mean", "median", "min", "max"]
    ).round(2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python build_jewellery_sample.py path/to/jewelry.csv")
        sys.exit(1)

    df = load(sys.argv[1])
    picked, gold_with_gem = pick_sample(df)

    print(f"{len(df)} total rows loaded")
    print(f"metal counts:\n{df['metal'].value_counts()}\n")

    print("sample rows:")
    for r in picked:
        print(f"  {r['event_time'][:10]} | {r['category_code']} | {r['metal']} | "
              f"{r['gem']} | ${r['price']:.2f}")

    print("\nprice summary by category (gold, gem stated):")
    print(price_summary(gold_with_gem))
