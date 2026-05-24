# Model Card / Governance Stub

## Tool

NEXUS Travel Rule Control Tower

## Intended use

Support a Coinbase Chief Compliance Officer in routing DPT transfers under US, Singapore and global strict Travel Rule configurations. The tool identifies whether Travel Rule data is required, whether required fields are missing, and whether a transaction should be approved, reviewed or blocked.

## Not intended use

The tool should not be used as a standalone money-laundering detection model, a sanctions screening engine, a consumer-facing explanation system, or a substitute for legal advice.

## Inputs

- Transaction amount in USD
- Customer region and destination jurisdiction
- Counterparty type, including hosted VASP or unhosted wallet
- Presence or absence of originator and beneficiary information
- Chain risk score, sanctions hit flag and adverse media flag
- Customer tenure and 24-hour transaction velocity

## Jurisdiction layer

Rules are stored in `config/jurisdiction_rules.json`. Each jurisdiction defines threshold, required fields, unhosted-wallet treatment, review thresholds, block thresholds and retention assumptions. The rules are intentionally externalized so policy can be updated without rewriting the scoring code.

## Decision logic

1. Check whether the transaction crosses the jurisdictional threshold.
2. Check whether required Travel Rule fields are present.
3. Block sanctions hits and transactions with missing required information.
4. Route high-risk or unhosted-wallet transfers to manual review.
5. Approve with the relevant data retention/audit label if no hard stop applies.

## Performance and monitoring

The synthetic evaluation reports false positive and false negative rates against simulated labels. These labels are not real AML ground truth. In production, monitoring should focus on alert quality, reviewer overturn rates, confirmed suspicious activity, consumer harm, data completeness and regional bias.

## Failure modes

- Rule change mid-period: historical cases may need re-evaluation under both old and new rules.
- Jurisdictional misconfiguration: US threshold accidentally applied to Singapore-touching transfers.
- Data quality failure: missing fields may cause avoidable blocks.
- Model drift: risk score may over-flag regions underrepresented in training data.
- Contradictory rules: one jurisdiction may prioritize velocity while another requires additional friction.

## Human judgement gates

Human review is required for sanctions hits, unhosted wallets above the jurisdiction risk threshold, model-drift alerts, disputed blocks, and cross-border cases where the strictest-rule approach creates material consumer harm.
