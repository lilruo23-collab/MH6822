# Task 3 One-Page Summary: NEXUS Travel Rule Control Tower

## Design choice

The tool is a jurisdiction-aware Travel Rule control layer for Coinbase-style digital payment token transfers. It is built for the Chief Compliance Officer, not for consumers directly. Its commercial promise is simple: the same transaction can be treated differently under US and Singapore rules, and a spreadsheet cannot reliably track those differences across changing thresholds, missing customer information, unhosted wallets and audit evidence.

## What the prototype does

The prototype takes synthetic transaction data and applies a jurisdiction configuration file. The US configuration uses a USD 3,000 threshold and prioritizes transaction velocity unless the transaction crosses that threshold or shows independently high AML risk. The Singapore configuration uses a lower S$1,500 threshold, requires basic originator and beneficiary data even below the enhanced threshold, and sends more unhosted-wallet activity to enhanced due diligence.

The output changes depending on which jurisdiction is active. In the synthetic dataset of 500 transfers, 58 transactions require enhanced Travel Rule data under the US configuration, while 345 require enhanced data under the Singapore configuration. 287 transfers sit in the practical conflict zone: not enhanced under the US threshold but enhanced under Singapore's threshold. This is the core regulatory divergence from Task 1 made operational rather than decorative.

## Why this is not just a memo or spreadsheet

A memo can describe the rule difference once. A spreadsheet can flag obvious thresholds. The tool adds four things that a static spreadsheet cannot: versioned jurisdiction rules, data completeness checks, risk-based routing, and an audit trail showing why a transaction was approved, reviewed or blocked. This matters because the operational harm is not only a fine. The harm is misconfiguration: a US-speed setting accidentally applied to a Singapore-touching transaction.

## What it does not do

It does not detect money laundering by itself. It uses a deliberately simple behavioral risk score and synthetic labels only to demonstrate the workflow. It does not solve the privacy problem created by collecting more Travel Rule information. It does not give consumers a transparency interface, because the Task 2 values audit honestly recognized that the paying customer is the CCO. It also does not replace human judgement: sanctions hits, unhosted wallet reviews, model drift, and rule-change conflicts remain human escalation points.

## Honest limitation

The prototype is strongest as a compliance architecture and threshold demonstration. With more time and real data, I would add live rule feeds, case-management integration, bias monitoring by region, regulator-specific reporting packs, and a human-review quality audit to test whether reviewers are actually improving outcomes rather than rubber-stamping alerts.
