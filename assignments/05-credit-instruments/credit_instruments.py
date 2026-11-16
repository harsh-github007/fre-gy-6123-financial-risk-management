"""Credit instrument calculations for the RMN5 case study."""

import math



print("=== Q1 Intensity model ===")

p1 = 0.0125

lam = -math.log(1 - p1)

S = lambda t: math.exp(-lam * t)

q1_3 = S(2) - S(3)

print(f"lambda = {lam:.8f} ({lam*1e4:.4f} bp)")

print(f"S(2) = {S(2):.8f}, S(3) = {S(3):.8f}, P(2<tau<=3) = {q1_3:.8f}")



print("\n=== Q2 CDS bootstrap & risky bond ===")

s1, s2, R, r = 0.0120, 0.0155, 0.40, 0.02

L=1-R

Z = lambda t: math.exp(-r * t)

S1 = L / (L + s1)

S2 = Z(1) * (L * 1.0 - (L + s2) * S1) / (Z(2) * (L + s2)) + L * S1 / (L + s2)

# check: premium leg == loss leg for 2y

pl = s2 * (Z(1) * S1 + Z(2) * S2)

ll = L * (Z(1) * (1 - S1) + Z(2) * (S1 - S2))

print(f"Z1 = {Z(1):.8f}, Z2 = {Z(2):.8f}")

print(f"S1 = {S1:.8f}, S2 = {S2:.8f} (PL={pl:.8f}, LL={ll:.8f})")

lam1 = -math.log(S1); lam2 = -math.log(S2 / S1)

print(f"implied fwd hazard yr1 = {lam1:.6f}, yr2 = {lam2:.6f}")

F, c = 100.0, 0.05




cpn1 = F * c * (R + L * S1) * Z(1)

cpn2 = F * c * (R + L * S2) * Z(2)

prin = F * (R + L * S2) * Z(2)

B_deck = cpn1 + cpn2 + prin

print(f"Deck formula: coupon1 {cpn1:.6f}, coupon2 {cpn2:.6f}, principal {prin:.6f}, B = {B_deck:.6f}")

# alternative: coupons only on survival, R*F paid at maturity on default

B_alt = F * c * S1 * Z(1) + F * (1 + c) * S2 * Z(2) + R * F * (1 - S2) * Z(2)

B_rf = F * c * Z(1) + F * (1 + c) * Z(2)

print(f"Alt (coupons lost on default): B = {B_alt:.6f}; risk-free bond = {B_rf:.6f}")



print("\n=== Q3 CVA ===")

lamc, LGD, y = 0.025, 0.65, 0.03

EE = {1: 850_000, 2: 1_200_000}

Sc = lambda t: math.exp(-lamc * t)

cva = 0

for t in (1, 2):

  pd = Sc(t - 1) - Sc(t)

  df = 1 / (1 + y) ** t

  term = LGD * EE[t] * pd * df

  cva += term

  print(f"t={t}: S={Sc(t):.8f} PD={pd:.8f} DF={df:.8f} EL={LGD*EE[t]*pd:,.2f} PV={term:,.2f}")

print(f"CVA = {cva:,.2f}")



print("\n=== Q4 CDX trade ===")

N = 50_000_000




ig0, hy0, cig, chy = 0.0110, 0.0350, 0.01, 0.05

dig0, dhy0, ig1, hy1, dig1, dhy1 = 4.75, 4.50, 0.0160, 0.0550, 3.85, 3.80

up_ig = N * (ig0 - cig) * dig0    # sell IG protection: seller receives (spread>coupon)

up_hy = N * (chy - hy0) * dhy0      # buy HY protection: buyer receives (spread<coupon)

net0 = up_ig + up_hy

print(f"t=0: IG received {up_ig:,.2f}; HY received {up_hy:,.2f}; net received {net0:,.2f}")

un_ig = -N * (ig1 - cig) * dig1 # buy IG protection to close: buyer pays

un_hy = N * (hy1 - chy) * dhy1      # sell HY protection to close: seller receives

mtm1 = un_ig + un_hy

print(f"t=1: IG unwind {un_ig:,.2f}; HY unwind {un_hy:,.2f}; net {mtm1:,.2f}")

cpn = N * cig - N * chy

print(f"net coupons {cpn:,.2f}")

print(f"Total PnL = {net0 + mtm1 + cpn:,.2f}")



print("\n=== Q5 Repo ===")

face, px0, px3, rr, T, IM = 150_000_000, 1.035, 1.06, 0.051, 14, 1.02

mv0 = face * px0

PP = mv0 / IM

RP = PP * (1 + rr * T / 360)

loan3 = PP * (1 + rr * 3 / 360)

mv3 = face * px3

vm = IM * loan3 - mv3

print(f"MV0 {mv0:,.2f} PP {PP:,.2f} haircut {1-PP/mv0:.4%} interest {RP-PP:,.2f} RP {RP:,.2f}")

print(f"day3 loan {loan3:,.2f} required collateral {IM*loan3:,.2f} MV3 {mv3:,.2f} VM {vm:,.2f}")




print("\n=== Q6 Excess return ===")

S0, D, S1_, PD6, RR6 = 0.0220, 6.2, 0.0285, 0.015, 0.45

LGD6 = 1 - RR6

dS = S1_ - S0

x1 = -D * dS

x2 = 0.5 * S0 - D * dS - 0.5 * PD6 * LGD6

be = (0.5 * S0 - 0.5 * PD6 * LGD6) / D

print(f"inst {x1:.4%}; 6m {x2:.4%}; breakeven dS {be*1e4:.4f} bp -> spread {(S0+be)*1e4:.4f} bp")

cash_vm = mv3 / IM - loan3

print(f"securities returned (deck convention) {-vm:,.2f}; cash alternative {cash_vm:,.2f}; short loss {face*(px3-px0):,.2f}")
