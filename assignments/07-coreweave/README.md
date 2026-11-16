# CoreWeave | Private credit and equity risk

**Valuation date** · 30 October 2026  
**Forecast horizon** · 2027–2031  
**Model** · [`coreweave.py`](coreweave.py)

How much debt can a capital-intensive cloud provider service when deployment slips, and what is left for creditors and equity holders when funding runs short? This case models three operating scenarios and traces cash flows through debt service, refinancing, and creditor recoveries.

| Scenario | DCF per share | Minimum DSCR | Unfunded need | Parent unsecured recovery | CCAC IV recovery |
|:--|--:|--:|--:|--:|--:|
| Base | $0.00 | 1.06× | $0m | 59% | 96% |
| Upside | $94.74 | 1.34× | $0m | 100% | 100% |
| Downside | $0.00 | 0.41× | $7,487m | 22% | 72% |

The base and upside recovery estimates use a hypothetical 2027 stress. The downside case triggers a modeled payment default. The DCF column uses the perpetuity method with an equity floor of zero. The script also prints an exit-multiple cross-check.

## Reproduce the analysis

```sh
python3 coreweave.py
```

Python 3.8+ · Standard library only · Runs offline

| Model stage | What to look for |
|:--|:--|
| Operating forecast | Backlog conversion, new signings, renewals, delivery delays, and capital expenditure |
| Funding and valuation | Debt-service coverage ratio (DSCR), borrowing limits, equity issuance, and dilution |
| Recovery waterfall | Asset-level collateral, parent unsecured claims, and CCAC IV lender recovery |
| Expected loss | Historical rating-cohort default inputs, loan amortization, and the five-year default rate at which expected loss equals modeled margin and fee income |

The forecast estimates funding shortfalls and coverage. Default rates for the expected-loss calculation come from historical rating cohorts. Inputs and scenario assumptions are embedded in the script. Dollar amounts are in USD millions unless the output specifies otherwise.

## Repository scope

This release includes the research report, the Excel workbook, and the standalone Python model. The report omits assignment prompts and submission logs. No open-source license has been selected.

## Project files

[Assignment report](report.docx) · [Model workbook](workbook.xlsx)

The public workbook retains the regression outputs and model formulas. Historical price observations are excluded.

[Course portfolio](../../README.md)
