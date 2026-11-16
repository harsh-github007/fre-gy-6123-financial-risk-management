"""Forward pricing, mark-to-market, and put–call parity calculations."""

import math

def q1(S0=4000.0, r=0.05, q=0.02, T=0.75, premium=0.03):
    F = S0 * math.exp((r - q) * T)
    F_mkt = F * (1 + premium)
    units = math.exp(-q * T)            # index units bought today (dividends reinvested -> 1 unit at T)
    cost = S0 * units                   # amount borrowed today
    repay = cost * math.exp(r * T)      # loan repayment at T (= F)
    profit_T = F_mkt - repay
    return dict(F=F, F_mkt=F_mkt, units=units, cost=cost, repay=repay,
                profit_T=profit_T, profit_PV=profit_T * math.exp(-r * T),
                carry=r - q, growth=math.exp((r - q) * T))

def q2(S0=100.0, r=0.04, T=1.0, t=0.5, St=82.0):
    F0 = S0 * (1 + r) ** T
    pvF = F0 * (1 + r) ** (-(T - t))
    V_long = St - pvF
    Ft = St * (1 + r) ** (T - t)        # new forward price for remaining 6m
    return dict(F0=F0, pvF=pvF, V_long=V_long, Ft=Ft, diff_T=Ft - F0,
                max_exposure_short=pvF)

def q3(S=100.0, K=105.0, T=0.5, r=0.03, c=4.0, p=9.0):
    pvK = K * math.exp(-r * T)
    lhs = c + pvK                       # fiduciary call
    rhs = p + S                         # protective put
    gap = rhs - lhs
    implied_p = c + pvK - S
    implied_c = p + S - pvK
    F = S * math.exp(r * T)
    synth_fwd = c - p                   # long call + short put (market)
    fair_synth = S - pvK
    rows = []
    for ST in (80, 95, 105, 115, 130):
        payoff = max(ST - K, 0) - max(K - ST, 0) + K - ST
        rows.append((ST, max(ST - K, 0), -max(K - ST, 0), -ST, K, payoff))
    return dict(pvK=pvK, lhs=lhs, rhs=rhs, gap=gap, gap_T=gap * math.exp(r * T),
                implied_p=implied_p, implied_c=implied_c, F=F,
                synth_fwd=synth_fwd, fair_synth=fair_synth, rows=rows,
                pv_F_minus_K=(F - K) * math.exp(-r * T))

if __name__ == "__main__":
    for name, fn in (("Q1", q1), ("Q2", q2), ("Q3", q3)):
        print(name)
        for k, v in fn().items():
            print(f"  {k}: {v}")
