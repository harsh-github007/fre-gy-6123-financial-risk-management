# Financial Risk Management

**NYU Tandon · FRE-GY 6123**

Seven case studies covering operational controls, market risk, derivatives, and credit. Each case page outlines the analysis and the assumptions behind it.

| Assignment | Case study | Methods |
|:--|:--|:--|
| RMN1 | [Madoff and operational risk](assignments/01-madoff-operational-risk/) | Strategy replication, exposure mapping, due diligence |
| RMN2 | [Rates and fixed income](assignments/02-rates-and-fixed-income/) | Duration, convexity, benchmark rates, forward curves |
| RMN3 | [FX and equity](assignments/03-fx-and-equity/) | Carry trades, interest parity, equity valuation |
| RMN4 | [Derivatives](assignments/04-derivatives/) | Cash-and-carry, put–call parity, hedge sensitivity |
| RMN5 | [Credit instruments](assignments/05-credit-instruments/) | CDS calibration, CVA, repo, spread duration |
| RMN6 | [Structural credit risk](assignments/06-structural-credit-risk/) | Ratings migration, Merton model, expected loss |
| RMNF1 Part A | [CoreWeave private credit and equity](assignments/07-coreweave/) | Three-case cash flow forecast, debt service, creditor recovery |

## Run the CoreWeave model

```sh
python3 assignments/07-coreweave/coreweave.py
```

The script runs offline with Python 3.8+ and prints scenario valuations, debt-service coverage, funding gaps, creditor recoveries, and expected-loss calculations.

## Scope

This portfolio contains assignment summaries and standalone Python calculations for derivatives, credit instruments, and CoreWeave. No open-source license has been selected.
