"""Jurisdiction-aware Travel Rule prototype for Task 3."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class Decision:
    travel_rule_required: bool
    action: str
    missing_fields: list[str]
    reason: str


def load_rules(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))["jurisdictions"]


def missing_fields(row: pd.Series, fields: list[str]) -> list[str]:
    return [field for field in fields if not bool(row[field])]


def evaluate_transaction(row: pd.Series, rule: dict[str, Any]) -> Decision:
    above_threshold = float(row["amount_usd"]) >= float(rule["threshold_usd"])
    required_fields = (
        rule["required_fields_above_threshold"] if above_threshold else rule["minimum_fields_below_threshold"]
    )
    missing = missing_fields(row, required_fields)
    travel_rule_required = above_threshold or bool(required_fields)

    if bool(row["sanctions_screen_hit"]) and rule["unhosted_wallet_policy"]["block_if_sanctions_hit"]:
        return Decision(travel_rule_required, "BLOCK", missing, "Sanctions screen hit")

    if missing and travel_rule_required:
        return Decision(travel_rule_required, "BLOCK", missing, "Required Travel Rule data missing")

    if float(row["chain_risk_score"]) >= float(rule["block_threshold"]):
        return Decision(travel_rule_required, "BLOCK", missing, "AML risk score exceeds block threshold")

    if row["counterparty_type"] == "unhosted_wallet":
        if float(row["chain_risk_score"]) >= float(rule["unhosted_wallet_policy"]["manual_review_if_risk_score_gte"]):
            return Decision(travel_rule_required, "REVIEW", missing, "Unhosted wallet requires EDD/manual review")

    if float(row["chain_risk_score"]) >= float(rule["risk_review_threshold"]):
        return Decision(travel_rule_required, "REVIEW", missing, "AML risk score exceeds review threshold")

    if above_threshold:
        return Decision(travel_rule_required, "APPROVE_WITH_TRAVEL_RULE_DATA", missing, "Threshold crossed")

    if required_fields:
        return Decision(travel_rule_required, "APPROVE_WITH_BASIC_DATA", missing, "Below enhanced threshold; basic data retained")

    return Decision(travel_rule_required, "APPROVE", missing, "Below jurisdictional threshold and no elevated risk")


def apply_rules(data: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    output = data.copy()
    for jurisdiction, rule in rules.items():
        decisions = [evaluate_transaction(row, rule) for _, row in data.iterrows()]
        prefix = jurisdiction.lower()
        output[f"{prefix}_above_threshold"] = data["amount_usd"] >= float(rule["threshold_usd"])
        output[f"{prefix}_travel_rule_required"] = [d.travel_rule_required for d in decisions]
        output[f"{prefix}_action"] = [d.action for d in decisions]
        output[f"{prefix}_missing_fields"] = [";".join(d.missing_fields) for d in decisions]
        output[f"{prefix}_reason"] = [d.reason for d in decisions]

    output["us_vs_sg_different"] = (
        (output["us_travel_rule_required"] != output["sg_travel_rule_required"])
        | (output["us_action"] != output["sg_action"])
    )
    return output


def summarize(evaluated: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for jurisdiction in rules:
        prefix = jurisdiction.lower()
        action_counts = evaluated[f"{prefix}_action"].value_counts()
        blocked_or_review = evaluated[f"{prefix}_action"].isin(["BLOCK", "REVIEW"])
        false_positive = (blocked_or_review) & (~evaluated["simulated_illicit_label"])
        false_negative = (evaluated[f"{prefix}_action"].str.startswith("APPROVE")) & evaluated["simulated_illicit_label"]
        rows.append(
            {
                "jurisdiction": jurisdiction,
                "travel_rule_required": int(evaluated[f"{prefix}_travel_rule_required"].sum()),
                "above_threshold_enhanced_data": int(evaluated[f"{prefix}_above_threshold"].sum()),
                "block": int(action_counts.get("BLOCK", 0)),
                "review": int(action_counts.get("REVIEW", 0)),
                "approve_or_approve_with_data": int(len(evaluated) - action_counts.get("BLOCK", 0) - action_counts.get("REVIEW", 0)),
                "false_positive_rate": round(float(false_positive.mean()), 4),
                "false_negative_rate": round(float(false_negative.mean()), 4),
            }
        )
    return pd.DataFrame(rows)


def sensitivity(data: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for scale in [0.8, 1.0, 1.25, 1.5]:
        shifted = data.copy()
        shifted["amount_usd"] = shifted["amount_usd"] * scale
        evaluated = apply_rules(shifted, rules)
        for jurisdiction in ["US", "SG"]:
            prefix = jurisdiction.lower()
            rows.append(
                {
                    "amount_distribution_shift": scale,
                    "jurisdiction": jurisdiction,
                    "travel_rule_required": int(evaluated[f"{prefix}_travel_rule_required"].sum()),
                    "above_threshold_enhanced_data": int(evaluated[f"{prefix}_above_threshold"].sum()),
                    "manual_review_or_block": int(evaluated[f"{prefix}_action"].isin(["REVIEW", "BLOCK"]).sum()),
                    "different_from_other_jurisdiction": int(evaluated["us_vs_sg_different"].sum()),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, default=Path("config/jurisdiction_rules.json"))
    parser.add_argument("--data", type=Path, default=Path("data/synthetic_travel_rule_transactions.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    rules = load_rules(args.rules)
    data = pd.read_csv(args.data)
    evaluated = apply_rules(data, rules)
    summary = summarize(evaluated, rules)
    sens = sensitivity(data, rules)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(args.out_dir / "evaluated_transactions.csv", index=False)
    summary.to_csv(args.out_dir / "jurisdiction_summary.csv", index=False)
    sens.to_csv(args.out_dir / "sensitivity_analysis.csv", index=False)

    examples = evaluated[evaluated["us_vs_sg_different"]].head(12)
    examples.to_csv(args.out_dir / "jurisdiction_conflict_examples.csv", index=False)

    metrics = {
        "transactions": int(len(evaluated)),
        "us_travel_rule_required": int(evaluated["us_travel_rule_required"].sum()),
        "sg_travel_rule_required": int(evaluated["sg_travel_rule_required"].sum()),
        "us_enhanced_data_required": int(evaluated["us_above_threshold"].sum()),
        "sg_enhanced_data_required": int(evaluated["sg_above_threshold"].sum()),
        "different_us_vs_sg": int(evaluated["us_vs_sg_different"].sum()),
        "conflict_share": round(float(evaluated["us_vs_sg_different"].mean()), 4),
        "sg_extra_travel_rule_cases": int(
            ((~evaluated["us_travel_rule_required"]) & evaluated["sg_travel_rule_required"]).sum()
        ),
        "sg_extra_enhanced_cases": int(((~evaluated["us_above_threshold"]) & evaluated["sg_above_threshold"]).sum()),
    }
    (args.out_dir / "key_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
