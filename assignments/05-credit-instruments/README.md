# Credit instruments | Survival, spreads, and collateral

The assignment derives a constant-intensity survival curve and then uses default exposure to value CDS, risky bonds, and counterparty credit adjustments.

## CDS calibration

Solve for survival probabilities by equating the discounted premium and protection legs at each quoted tenor. Use the resulting curve to compare risky bond values under different recovery conventions.

## Counterparty and collateral

Discount period expected losses for credit valuation adjustment. For repo, calculate haircut, accrued financing, and variation margin from the collateral value and loan balance.

## Spread risk

Separate spread carry, the spread-duration price effect, and expected default loss. The worked bond example puts the six-month break-even spread near 231 basis points.

## Run the calculations

Reproduces the CDS bootstrap, credit valuation adjustment, CDX trade, repo margin, and bond excess return calculations. The script uses the Python standard library.

```sh
python3 assignments/05-credit-instruments/credit_instruments.py
```

[Course portfolio](../../README.md)
