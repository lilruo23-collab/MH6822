"""Generate synthetic crypto transfer data for Task 3.

The dataset is fictional. It is designed to stress the exact jurisdictional
problem from Task 1: transactions that are below the US Travel Rule threshold
but above Singapore's lower threshold.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ASSETS = ["USDC", "BTC", "ETH", "SOL"]
REGIONS = ["US", "Singapore", "EU", "Nigeria", "India", "UAE", "Hong Kong"]
DESTINATIONS = ["US", "Singapore", "EU", "Offshore", "High-risk corridor"]


def bounded(values: np.ndarray, low: float, high: float) -> np.ndarray:
    return np.minimum(np.maximum(values, low), high)


def make_dataset(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    amount = rng.lognormal(mean=7.15, sigma=0.95, size=rows)
    amount = bounded(amount, 50, 25000).round(2)

    # Deliberately over-sample the policy conflict band: USD 1,110-3,000.
    band_mask = rng.random(rows) < 0.34
    amount[band_mask] = rng.uniform(1120, 2990, size=band_mask.sum()).round(2)

    customer_region = rng.choice(REGIONS, size=rows, p=[0.35, 0.22, 0.16, 0.08, 0.08, 0.05, 0.06])
    destination = rng.choice(DESTINATIONS, size=rows, p=[0.22, 0.24, 0.24, 0.18, 0.12])
    counterparty = rng.choice(["hosted_vasp", "unhosted_wallet"], size=rows, p=[0.72, 0.28])
    asset = rng.choice(ASSETS, size=rows, p=[0.58, 0.18, 0.18, 0.06])

    tenure = rng.integers(1, 2200, size=rows)
    velocity = rng.poisson(lam=2.8, size=rows) + rng.binomial(1, 0.09, size=rows) * rng.integers(8, 25, size=rows)
    sanctions = rng.random(rows) < 0.012
    adverse_media = rng.random(rows) < 0.045

    region_risk = pd.Series(customer_region).map(
        {"US": 8, "Singapore": 10, "EU": 9, "Nigeria": 28, "India": 18, "UAE": 15, "Hong Kong": 13}
    ).to_numpy()
    dest_risk = pd.Series(destination).map(
        {"US": 4, "Singapore": 5, "EU": 6, "Offshore": 18, "High-risk corridor": 34}
    ).to_numpy()
    chain_noise = rng.normal(0, 8, rows)
    chain_risk_score = (
        12
        + region_risk
        + dest_risk
        + (counterparty == "unhosted_wallet") * 16
        + (amount > 3000) * 8
        + (velocity >= 8) * 12
        + sanctions * 55
        + adverse_media * 18
        + chain_noise
    )
    chain_risk_score = bounded(chain_risk_score, 1, 99).round(1)

    # Missing information is more likely for unhosted wallets and newer users.
    base_missing = 0.03 + (counterparty == "unhosted_wallet") * 0.12 + (tenure < 60) * 0.08
    originator_name = rng.random(rows) > base_missing * 0.4
    originator_account = rng.random(rows) > base_missing * 0.45
    beneficiary_name = rng.random(rows) > base_missing * 0.55
    beneficiary_account = rng.random(rows) > base_missing * 0.5
    originator_address = rng.random(rows) > (base_missing + 0.08)
    originator_id = rng.random(rows) > (base_missing + 0.10)

    # Simulated ground truth is only for evaluation, not for operational use.
    illicit_probability = (
        0.01
        + sanctions * 0.55
        + adverse_media * 0.13
        + (chain_risk_score > 80) * 0.16
        + (destination == "High-risk corridor") * 0.05
        + (counterparty == "unhosted_wallet") * 0.035
    )
    illicit_probability = bounded(illicit_probability, 0.002, 0.8)
    illicit = rng.random(rows) < illicit_probability

    return pd.DataFrame(
        {
            "tx_id": [f"TX-{seed}-{i:04d}" for i in range(1, rows + 1)],
            "customer_region": customer_region,
            "destination_jurisdiction": destination,
            "asset": asset,
            "amount_usd": amount,
            "counterparty_type": counterparty,
            "customer_tenure_days": tenure,
            "transaction_velocity_24h": velocity,
            "chain_risk_score": chain_risk_score,
            "sanctions_screen_hit": sanctions,
            "adverse_media_flag": adverse_media,
            "originator_name": originator_name,
            "originator_account": originator_account,
            "originator_address": originator_address,
            "originator_id": originator_id,
            "beneficiary_name": beneficiary_name,
            "beneficiary_account": beneficiary_account,
            "simulated_illicit_label": illicit,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=500)
    parser.add_argument("--seed", type=int, default=6822)
    parser.add_argument("--out", type=Path, default=Path("data/synthetic_travel_rule_transactions.csv"))
    args = parser.parse_args()

    data = make_dataset(args.rows, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.out, index=False)
    print(f"Wrote {len(data)} synthetic transactions to {args.out}")


if __name__ == "__main__":
    main()
