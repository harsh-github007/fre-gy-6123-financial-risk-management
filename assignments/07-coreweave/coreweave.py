"""
CoreWeave forecast, valuation, and credit risk model.

The standalone Python model reproduces the submitted workbook calculations,
including break-even inputs solved by bisection. Run from the repository root
with python3 model/coreweave.py (Python 3.8+, standard library only).

Units
    USD million unless stated. Rates are fractions. Shares are in millions.

Model conventions (version 8)
    - Cost of equity: CAPM with the 10-year Treasury yield and the implied equity risk
      premium measured over that same yield (MKT-012, MKT-016).
    - WACC: diluted market equity weight; the debt cost equals the scenario borrowing rate.
    - Interest: borrowing rate x gross debt (net debt + cash held) less interest on cash.
    - Capital: each capex vintage leaves productive capital when its economic life L ends
      (the same L as the terminal value). Capex restores the capital needed for next
      year's revenue (capital intensity k).
    - Terminal value: steady-state capex keeps gross capital growing at g with an
      economic life of L years: capex/K = (g/(1+g)) / (1-(1+g)^-L).
    - 2026 capex bridge: deployment capex (asset recognition) and cash purchases differ.
      Gross capital grows by H2 deployment. H2 cash = cash ratio x H2 deployment plus the
      unpaid part of H1 deployment; the unpaid part of H2 deployment is paid in 2027.
    - Financing: an ASSUMED financing capacity limits new borrowing to a net debt multiple of
      EBITDA. Shares are sold at a discount to a stressed market price, up to a yearly limit.
      Existing holders keep N / (N + new shares) of (equity value + PV of proceeds).
    - Convertibles: at end 2031, conversion value above the capped-call cap prices dilutes
      shareholders (net share settlement, principal in cash). A test without capped calls
      is also reported.
    - Sources and uses each year: need = principal + interest - shield - FCFF. New borrowing is
      limited so that net debt after it stays within the assumed capacity; the ceiling never
      extinguishes existing debt. Shares are sold for the rest up to a yearly limit. A remaining
      shortfall, after spending the usable share of parent cash, is a payment default: maturing principal is not repaid (it stays owed), then interest
      is not paid (accrued claim), then vendor invoices are not paid.
    - Recovery value: going-concern restructuring (forward FCFF, distress discount) or liquidation
      (forced-liquidation ratio x net PP&E). Both are reported.
    - Distress date: the first year with a cash shortfall (a modeled payment default); if there
      is none, a hypothetical stress at end 2027. A DSCR below 1 is reported as a coverage
      stress only and never sets the date. CCAC IV collateral is carved out of the
      asset-level collateral pool first, so each asset is counted once.
    - Cash at default (ASSUMED split, not disclosed): parent cash (spent first, any rest to
      parent creditors), cash in asset-level borrower subsidiaries (added to those lenders'
      collateral), minimum operating liquidity (kept in a going concern, paid out in liquidation).
    - Credit cross-check (credit_check): the DDTL 2.1 expected loss year by year (default
      intensity from the B+ cohort, start-of-year exposure, 20% amortization, 72% recovery,
      margin and fee), the default rate at which expected loss equals margin income plus the fee
      (solved by bisection in the five-year model), and the note prices at which the yield spread equals the model expected
      loss. This calculation was implemented independently of the workbook formulas.
"""
import math
YEARS = [2027, 2028, 2029, 2030, 2031]
VAL = 2026 + 10 / 12                     # valuation date, 30 October 2026, as a year fraction
T_HOR = 1888 / ((365 * 5 + 366) / 6)     # 30 Oct 2026 to 31 Dec 2031, actual/actual (Excel YEARFRAC basis 1)

# ------------------------------------------------------------ common inputs (workbook: Model inputs)
COMMON = dict(
    rev26=12800,             # FY2026 revenue, guidance midpoint (OPS-052, OPS-053)
    h1rev=4653,              # H1 2026 revenue (FIN-006)
    h1ebitda=2347,           # H1 2026 operating loss -193 plus D&A 2,540 (FIN-041, FIN-075)
    capex26=37000,           # FY2026 deployment capex guidance midpoint (OPS-056, OPS-057)
    h1dep=16139,             # H1 2026 deployment capex (OPS-037)
    h1cash=14117,            # H1 2026 cash purchases of property and equipment (FIN-107)
    h2int=1800,              # two quarters at the Q3 interest guidance midpoint (OPS-064, OPS-065)
    h2tax=146,               # H2 2026 tax set equal to H1 2026 (FIN-062)
    debt_jun=35551,          # gross debt principal, 30 June 2026 (OPS-068)
    cash=5524,               # cash and cash equivalents, 30 June 2026, held constant (FIN-162)
    gppe_jun=52622,          # gross property and equipment, 30 June 2026 (FIN-217)
    nppe_jun=46736,          # net property and equipment, 30 June 2026 (FIN-214)
    h1da=2540,               # H1 2026 depreciation and amortization (FIN-075), used for H2 2026
    rpo=103700,              # remaining performance obligations, 30 June 2026 (FIN-194)
    b1=.41, b2=.39, b3=.20,  # RPO recognized in months 1-24, 25-48, 49-78 (OPS-008 to OPS-010)
    committed=.98,           # share of revenue from committed contracts (OPS-007)
    q3=25000 / 5,            # early-Q3 commitments (OPS-042) over a five-year duration (OPS-030)
    ramp=[.3, .8, 1, 1, 1],  # delivery ramp of those commitments (assumption)
    vint={2023: 2943, 2024: 8702, 2025: 10309},  # FY2023-FY2025 cash capex by vintage (FIN-103 to FIN-105)
    sched={2027: 6184, 2028: 4416, 2029: 2421, 2030: 3221, 2031: 1750 + 2750 + 2588},  # principal due
    dep=.125,                # depreciation rate on average gross PP&E, 2027-2031 (assumption)
    taxc=.15, taxT=.21,      # cash tax rate 2027-2031 and terminal tax rate (assumptions)
    rf=.0494,                # 10-year Treasury par yield, 30 Oct 2026 (MKT-012)
    erp=.037,                # implied equity risk premium over the 10-year Treasury (MKT-016)
    beta=1.87754691476371,   # weekly regression beta (Equity returns sheet)
    rc=.0394,                # interest earned on cash: overnight SOFR (MKT-015)
    basic=551.536602,        # Class A and Class B shares, 31 July 2026 (MKT-020, MKT-021)
    rsu=31, opt=24, optK=1.84, war=4, warK=1.5495,  # RSUs, options and warrants with exercise prices
    price=54.87,             # CRWV close, 30 October 2026 (MKT-019)
    D=42151,                 # June debt principal plus known additions (WACC debt weight)
    R=1200,                  # revolver drawn (OPS-080)
    U=10029 + 6588 + 4200 + 189,   # parent unsecured claims: senior notes, convertibles, Magnetar
    NR=3719,                 # non-recourse debt principal (OPS-070)
    UNmat={2029: 189, 2030: 2000, 2031: 1750 + 2750 + 2588},  # parent unsecured maturities by year
    IV=3190 + 3000, amr=.20,  # CCAC IV principal June 2026 and assumed amortization per year
    conv=[(2588, 9.2764, 215.60), (4000, 8.3612, 230.00), (4200, 10.2194, 199.70)],  # principal, shares per 1,000, cap price
    alpha=.60,               # share of distressed operating value pledged to asset-level lenders
    distress=.80,
    tstress=1)               # hypothetical stress date if no payment default: end 2027 (year index 1)

# ------------------------------------------------------------ scenario assumptions (yellow cells)
#   hc   RPO realization factor               d     delivery delay, months
#   q3f  realization of early-Q3 commitments  ns    further signings per year from 2028
#   rr   renewal rate                         rp    renewal price ratio
#   m    EBITDA margin                        k     capital intensity (capital per USD of revenue)
#   iR   borrowing rate                       g     terminal growth
#   life economic life of capital, years      L     lenders' maximum net debt / EBITDA
#   disc share issue discount to fair value   fmv   CCAC IV collateral value / loan at default
#   liq  liquidation ratio of used GPU servers
#   cr   cash share of H2 2026 deployment     sp    stressed share price / USD 54.87
#   q    yearly share-sale limit / diluted shares
#   cashuse share of June 2026 cash that can be spent before a payment default (rest: restricted
#           cash in borrower accounts and a minimum operating balance)
#   cashsub share of June cash held in asset-level borrower accounts (collateral of those lenders);
#           the rest of the unusable cash is minimum operating liquidity
#   vbasis distressed value: 0 = going-concern restructuring (distress x forward EV), 1 = liquidation (liq x net PP&E)
#   unew unsecured share of debt raised after June 2026 (the rest is guaranteed asset-level debt)
BASE = dict(hc=.92, d=3, q3f=1.0, ns=3000, rr=.6, rp=.6, m=.55, k=3.3, iR=.09, g=.025,
            life=8, L=6.0, disc=.10, fmv=1.4, liq=126000 / 195000, cr=14117 / 16139, sp=.6, q=.2, unew=.5, vbasis=0, cashuse=.5, cashsub=.25)
UP = dict(hc=.97, d=0, q3f=1.0, ns=6000, rr=.8, rp=.75, m=.60, k=3.0, iR=.08, g=.03,
          life=9, L=6.5, disc=.05, fmv=1.4, liq=173000 / 195000, cr=14117 / 16139, sp=.9, q=.2, unew=.5, vbasis=0, cashuse=.5, cashsub=.25)
DOWN = dict(hc=.80, d=9, q3f=.7, ns=0, rr=.3, rp=.45, m=.48, k=3.7, iR=.11, g=.015,
            life=6, L=5.0, disc=.20, fmv=1.0, liq=126000 / 195000, cr=14117 / 16139, sp=.3, q=.2, unew=.5, vbasis=0, cashuse=.5, cashsub=.25)


def diluted_shares(C):
    """Class A and B plus RSUs, plus options and warrants by the treasury-stock method."""
    P = C['price']
    return C['basic'] + C['rsu'] + C['opt'] * (1 - C['optK'] / P) + C['war'] * (1 - C['warK'] / P)


def run(p, C=COMMON):
    """Run one case. p holds the case assumptions. Returns a dictionary of results."""
    p = dict(p); p.setdefault('wadd', 0)
    o = {}
    N = diluted_shares(C); E = N * C['price']
    ke = C['rf'] + C['beta'] * C['erp']                          # required shareholder return
    we = E / (E + C['D'])
    w = we * ke + (1 - we) * p['iR'] * (1 - C['taxT']) + p['wadd']   # WACC
    o.update(ke=ke, wacc=w, N=N, E=E)
    # --- June RPO spread over calendar years
    h2rev = C['rev26'] - C['h1rev']; m26 = C['h1ebitda'] / C['h1rev']
    h2c = h2rev * C['committed']; rest = C['rpo'] * C['b1'] - h2c
    b2, b3 = C['rpo'] * C['b2'], C['rpo'] * C['b3']
    rpo = {2026: h2c, 2027: rest * 2 / 3, 2028: rest / 3 + b2 / 4, 2029: b2 / 2,
           2030: b2 / 4 + b3 / 5, 2031: b3 * 2 / 5}
    peak = max(rpo[y] for y in YEARS)
    prev = {2027: 2 * h2c, **{y: rpo[y - 1] for y in YEARS[1:]}}
    rev = {}
    for i, y in enumerate(YEARS):
        rev[y] = (p['hc'] * ((1 - p['d'] / 12) * rpo[y] + p['d'] / 12 * prev[y])
                  + C['q3'] * p['q3f'] * C['ramp'][i] + p['ns'] * max(0, y - 2027)
                  + p['rr'] * p['rp'] * max(0, peak - rpo[y]))
    o['rev'] = rev
    # --- 2026 capex bridge and net debt at 31 December 2026E
    h2dep = C['capex26'] - C['h1dep']                          # H2 deployment (asset recognition)
    h2cash = p['cr'] * h2dep + (C['h1dep'] - C['h1cash'])      # H2 cash purchases
    defer = (1 - p['cr']) * h2dep                              # unpaid H2 deployment, paid in 2027
    nd26 = C['debt_jun'] - C['cash'] + h2cash - h2rev * m26 + C['h2int'] + C['h2tax']
    o.update(nd26=nd26, h2dep=h2dep, h2cash=h2cash, defer=defer)
    # --- operating forecast and FCFF
    K = C['gppe_jun'] + h2dep; pv = 0; ops = []
    for i, y in enumerate(YEARS):
        nxt = rev[YEARS[i + 1]] if i < 4 else rev[y] * (1 + p['g'])
        ret = sum(v for vy, v in C['vint'].items() if vy + p['life'] == y)   # vintage retires after its economic life
        capex = max(0, p['k'] * nxt - (K - ret))                 # restore capital needed next year
        repl = min(capex, ret); growth = capex - repl
        K2 = K - ret + capex; da = C['dep'] * (K + K2) / 2; K = K2
        ebitda = p['m'] * rev[y]; ebit = ebitda - da; tax = C['taxc'] * max(ebit, 0)
        lag = defer if i == 0 else 0                              # deferred 2026 capex paid in 2027
        fcff = ebitda - tax - capex - lag
        pv += fcff * (1 + w) ** -(i + .5)                         # mid-year from 31 December 2026
        ops.append(dict(y=y, rev=rev[y], ebitda=ebitda, ret=ret, capex=capex, repl=repl, lag=lag,
                        growth=growth, K=K, da=da, ebit=ebit, tax=tax, fcff=fcff))
    g, life = p['g'], p['life']
    ratio = (g / (1 + g)) / (1 - (1 + g) ** -life)               # steady-state capex / gross capital
    eb = ops[-1]['ebitda'] * (1 + g); da32 = K * (1 + g / 2) / life
    fT = eb - C['taxT'] * max(0, eb - da32) - ratio * K * (1 + g)
    tv = max(0, fT / (w - g)); pvtv = tv * (1 + w) ** -5; ev = pv + pvtv
    eq_oct = (ev - nd26) / (1 + ke) ** (2 / 12)
    o.update(fT=fT, tv=tv, pvf=pv, pvtv=pvtv, ev=ev, eq_oct=eq_oct, ratio=ratio)
    # --- debt service, assumed financing capacity, share sales and unfunded gap
    price_iss = (1 - p['disc']) * p['sp'] * C['price']           # stressed issue price, USD/share
    cap_iss = p['q'] * N * price_iss                              # yearly share-sale capacity, USD m
    nd = nd26; pv_iss = 0; newsh = 0; rows = []
    cash_t = C['cash']; drawn = 0.0                                 # cash balance; usable share p['cashuse'] of June cash
    for r in ops:
        y = r['y']
        intr = p['iR'] * (nd + cash_t) - C['rc'] * cash_t
        shield = C['taxc'] * min(intr, max(r['ebit'], 0))
        sp_ = C['sched'][y]
        dscr = (r['ebitda'] - r['tax'] - r['repl']) / (intr + sp_)
        # cash sources and uses: uses = scheduled principal + interest - shield - FCFF (= need)
        need = sp_ + intr - shield - r['fcff']
        ndpre = nd + intr - shield - r['fcff']                    # net debt if the whole need were borrowed
        nd_after = nd - sp_                                       # existing debt after scheduled repayment
        bcap = max(0, p['L'] * r['ebitda'] - nd_after)            # new borrowing allowed by the assumed capacity
        borrow = min(max(need, 0), bcap)                          # new borrowing and refinancing obtained
        iss = min(max(0, need - borrow), cap_iss)                 # shares sold for the rest, up to the yearly limit
        pre = max(0, need - borrow - iss)
        draw = min(pre, p['cashuse'] * C['cash'] - drawn)         # usable cash is spent before a default
        drawn += draw
        unfunded = pre - draw                                     # cash shortfall: payments that cannot be made
        Sp = min(unfunded, sp_)                                   # 1st: maturing principal not repaid (stays owed)
        Si = min(unfunded - Sp, intr)                              # 2nd: interest not paid (accrued claim)
        Sc = unfunded - Sp - Si                                    # 3rd: unpaid vendor invoices
        tau = y + .5 - VAL                                    # 30 October 2026 to mid-year y
        newsh += iss / price_iss; pv_iss += iss * (1 + ke) ** -tau
        nd = nd_after + Sp + borrow + draw + min(0, need)          # funded net debt; spending cash raises net debt
        cash_t -= draw
        rows.append(dict(r, intr=intr, shield=shield, sp=sp_, dscr=dscr, need=need, ndpre=ndpre, bcap=bcap,
                         borrow=borrow, iss=iss, draw=draw, cash=cash_t, unfunded=unfunded, Sp=Sp, Si=Si, Sc=Sc, nd=nd, lev=nd / r['ebitda']))
        nd += Si + Sc                                              # after a default, unpaid amounts roll into next year's claims (illustrative)
    o['rows'] = rows
    v_raw = (eq_oct + pv_iss) / (N + newsh)                      # value per existing share
    o.update(price_iss=price_iss, cap_iss=cap_iss, pv_iss=pv_iss, v_raw=v_raw, ps=max(0, v_raw), newsh=newsh,
             iss=sum(r['iss'] for r in rows), unfunded=sum(r['unfunded'] for r in rows))
    # --- end-2031 price and convertible dilution above the capped-call cap prices
    Nt = N + newsh; eq31 = tv - rows[-1]['nd']
    p0 = max(eq31, 0) / Nt
    nconv = [(D * k / 1000, cap, 1000 / k) for D, k, cap in C['conv']]   # shares (m), cap price, conversion price
    act = [(n, cap) for n, cap, K_ in nconv if p0 > cap]
    p31 = (max(eq31, 0) + sum(n * cap for n, cap in act)) / (Nt + sum(n for n, _ in act))
    act2 = [(n, K_) for n, cap, K_ in nconv if p0 > K_]
    p31nc = (max(eq31, 0) + sum(n * K_ for n, K_ in act2)) / (Nt + sum(n for n, _ in act2))
    act2 = [(n, K_) for n, K_ in act2 if p31nc > K_]             # second pass: keep notes still in the money
    p31nc = (max(eq31, 0) + sum(n * K_ for n, K_ in act2)) / (Nt + sum(n for n, _ in act2))
    o.update(eq31=eq31, p31pre=p0, p31=p31, p31nc=p31nc, nconv=nconv,
             ret=(p31 / C['price']) ** (1 / T_HOR) - 1, retnc=(p31nc / C['price']) ** (1 / T_HOR) - 1,
             m2=p31 / (1 + ke) ** T_HOR)
    o['mindscr'] = min(r['dscr'] for r in rows); o['cumneed'] = sum(r['need'] for r in rows)
    net_ppe = []; npp = C['nppe_jun'] + h2dep - C['h1da']         # net PP&E end 2026 (H2 D&A = H1 D&A)
    for r in rows:
        npp = npp + r['capex'] - r['da']; net_ppe.append(npp)
    o['net_ppe'] = net_ppe
    # --- distress waterfall at the modeled default date
    idx = next((i for i, r in enumerate(rows) if r['unfunded'] > 0.5), None)
    actual = idx is not None                                     # modeled payment default (unfunded gap)
    if idx is None: idx = C['tstress'] - 1                       # otherwise a hypothetical stress date
    dsy = next((YEARS[i] for i, r in enumerate(rows) if r['dscr'] < 1), 0)   # coverage stress, not a default
    t = idx + 1; yd = YEARS[idx]
    evt = sum(rows[s_]['fcff'] * (1 + w) ** -(s_ + 1 - t - .5) for s_ in range(idx + 1, 5)) + tv * (1 + w) ** -(5 - t)
    gapd = rows[idx]['unfunded'] if actual else 0.0             # cash shortfall in the default year
    cash_d = rows[idx]['cash']                                    # cash left at the waterfall date
    gross = rows[idx]['nd'] + cash_d                             # funded debt, incl. maturing principal not repaid
    unpaid = (rows[idx]['Si'] + rows[idx]['Sc']) if actual else 0.0   # accrued interest and vendor claims, unsecured
    mat = sum(v for yy, v in C['UNmat'].items() if yy <= yd)
    IVt = C['IV'] * max(0, 1 - C['amr'] * (t + .5))
    new = gross - C['debt_jun'] + mat + (C['IV'] - IVt)           # debt raised after June 2026, incl. refinancing
    Ut = C['U'] - mat + p['unew'] * new                          # unsecured part of new debt joins the parent notes
    R, NR = C['R'], C['NR']
    Go = gross - R - Ut - NR - IVt                               # other guaranteed asset-level loans
    # distressed value: going-concern restructuring (vbasis 0) or liquidation of the GPU fleet (vbasis 1)
    gc = C['distress'] * evt
    liqv = p['liq'] * net_ppe[idx]
    # cash at default in three categories (all are unrestricted cash for accounting purposes)
    sub = min(p['cashsub'], 1 - p['cashuse']) * C['cash']        # held in asset-level borrower accounts: lenders' collateral
    free = p['cashuse'] * C['cash'] - (C['cash'] - cash_d)        # parent cash not spent before the default
    opc = cash_d - free - sub                                     # minimum operating liquidity
    base_v = liqv if p['vbasis'] == 1 else gc
    Vd = base_v + free + sub + (opc if p['vbasis'] == 1 else 0)   # operating cash stays in a going concern
    col = C['alpha'] * base_v + sub
    cIV = min(col, p['fmv'] * p['liq'] * IVt)                    # CCAC IV collateral, carved out first
    rest = col - cIV; cN = rest * NR / (Go + NR); cG = rest - cN
    rIVc = min(IVt, cIV); dIV = IVt - rIVc
    rGc = min(Go, cG); dG = Go - rGc
    pool = Vd - col + (cIV - rIVc) + (cG - rGc) + max(0, cN - NR)
    rR = min(R, pool); rhoU = min(1, (pool - rR) / (Ut + dIV + dG + unpaid))
    o.update(dyear=yd, actual=actual, cash_d=cash_d, sub=sub, free=free, opc=opc, gapd=gapd, unpaid=unpaid, gc=gc, liqv=liqv, netppe=net_ppe[idx], dsy=dsy, new=new, evt=evt, gross=gross, Ut=Ut, IVt=IVt, Go=Go, Vd=Vd, col=col, cIV=cIV, cG=cG, cN=cN,
             recU=rhoU, recR=rR / R, recNR=min(1, cN / NR), recG=(rGc + dG * rhoU) / Go,
             recIV=(rIVc + dIV * rhoU) / IVt if IVt > 0 else None,
             lossIV=dIV * (1 - rhoU), resid=max(0, pool - rR - Ut - dIV - dG - unpaid), cc=p['fmv'] * p['liq'])
    return o


def method3(o, mult, C=COMMON):
    """Value per share with an exit multiple on 2031E EBITDA instead of perpetual growth."""
    ev = o['pvf'] + mult * o['rows'][-1]['ebitda'] * (1 + o['wacc']) ** -5
    return max(0, ((ev - o['nd26']) / (1 + o['ke']) ** (2 / 12) + o['pv_iss']) / (o['N'] + o['newsh']))


def market_multiple(C=COMMON):
    """Market enterprise value at the cutoff divided by base 2027E EBITDA."""
    b = run(BASE)
    return (b['E'] + C['D'] - C['cash']) / b['rows'][0]['ebitda']


def bisect(f, lo, hi, n=70):
    """Root of f on [lo, hi]. f must change sign on the interval."""
    flo = f(lo)
    for _ in range(n):
        mid = (lo + hi) / 2; fm = f(mid)
        if (fm > 0) == (flo > 0): lo, flo = mid, fm
        else: hi = mid
    return (lo + hi) / 2


C = COMMON
vraw = lambda ch: run({**BASE, **ch})['v_raw']
be1 = bisect(lambda m: vraw({'m': m}) - C['price'], .40, .90)        # margin: value = market price
be2 = bisect(lambda m: vraw({'m': m}), .40, .90)                     # margin: equity value = 0
be3 = bisect(lambda d: run({**BASE, 'd': d})['rows'][0]['dscr'] - 1, 0, 12)   # delay: 2027 DSCR = 1.00x
be4 = bisect(lambda m: run({**BASE, 'm': m})['recU'] - 0.999999, .40, .90)    # margin: unsecured recover 100%
be6 = bisect(lambda d: run({**BASE, 'd': d})['unfunded'] - 0.5, 0, 12)          # delay: first unfunded gap
be5 = bisect(lambda k: vraw({'k': k}), 1.5, 3.3)                     # capital intensity: equity value = 0

SENS = [('RPO realization 82%', {'hc': .82}), ('Delivery delay 9 months', {'d': 9}),
        ('No further signings', {'ns': 0}), ('Weak renewals', {'rr': .3, 'rp': .45}),
        ('EBITDA margin 50%', {'m': .50}), ('EBITDA margin 60%', {'m': .60}),
        ('Capital intensity 3.7', {'k': 3.7}), ('Capital intensity 3.0', {'k': 3.0}),
        ('Borrowing rate 11%', {'iR': .11}), ('Capex paid fully in cash', {'cr': 1.0}),
        ('Stressed share price 30%', {'sp': .3}), ('Terminal growth 1.5%', {'g': .015}),
        ('Economic life 6 years', {'life': 6}), ('New debt all secured', {'unew': 0.0}), ('New debt all unsecured', {'unew': 1.0}), ('Leverage limit 5.0x', {'L': 5.0}),
        ('Discount rate +1 point', {'wadd': .01})]


# ---- Independent cross-check of the credit reconciliation (Credit analysis, sections 5 and 6)
CREDIT = {'pd5_bp': 0.1288,   # S&P five-year cumulative default, B+ cohort (MKT-039)
          'pd5_bm': 0.2203,   # S&P five-year cumulative default, B- cohort (MKT-049)
          'rce': 0.72,        # historical first-lien recovery (MKT-050)
          'mar': 0.0425,      # DDTL 2.1 margin over Term SOFR (CAP-003)
          'fee': 0.015,       # funding fee or OID, counted once (CAP-003)
          'sofr': 0.0394,     # overnight SOFR, 29 Oct 2026 (MKT-015)
          'cpn': 0.0975,      # coupon of the 9.75% senior notes due 2031 (CAP-011)
          'rf5': 0.0471}      # 5-year Treasury par yield, 30 Oct 2026 (MKT-010), matched to the note maturity


def price_30360(cpn, y, n=10, a_days=29, e_days=180):
    """Price per 100 of a semiannual bond, 30/360, as in the spreadsheet PRICE function.
    Settlement 30 Oct 2026, maturity 1 Oct 2031: 10 coupons left, 29 accrued days."""
    dsc = e_days - a_days; c = 100 * cpn / 2; f = dsc / e_days
    pv = sum(c / (1 + y / 2) ** (k - 1 + f) for k in range(1, n + 1)) + 100 / (1 + y / 2) ** (n - 1 + f)
    return pv - c * a_days / e_days


def el_gap(h, C=COMMON, K=CREDIT, disc=False):
    """Lifetime expected loss less (margin income + fee), per USD 1 funded, at default intensity h."""
    el = inc = 0.0
    for t in range(1, 6):
        b = 1 - C['amr'] * (t - 1); s0 = math.exp(-h * (t - 1)); s1 = math.exp(-h * t)
        df = (1 + K['sofr']) ** -(t - 0.5) if disc else 1.0
        el += (s0 - s1) * b * (1 - K['rce']) * df
        inc += K['mar'] * (s0 + s1) / 2 * (b - C['amr'] / 2) * df
    return el - inc - K['fee']


def credit_check(C=COMMON, K=CREDIT):
    """Year-by-year expected loss for DDTL 2.1 per USD 1 funded, written separately from the workbook."""
    h = -math.log(1 - K['pd5_bp']) / 5; hm = -math.log(1 - K['pd5_bm']) / 5
    rIV = run(BASE)['recIV']; rUb = run(BASE)['recU']; rUd = run(DOWN)['recU']
    eby = elh = elm = inc = pvi = pve = 0.0
    for t in range(1, 6):
        b = 1 - C['amr'] * (t - 1); s0 = math.exp(-h * (t - 1)); s1 = math.exp(-h * t); q = s0 - s1
        bal = (s0 + s1) / 2 * (b - C['amr'] / 2); df = (1 + K['sofr']) ** -(t - 0.5)
        eby += bal; elh += q * b * (1 - K['rce']); elm += q * b * (1 - rIV)
        inc += K['mar'] * bal; pvi += K['mar'] * bal * df; pve += q * b * (1 - K['rce']) * df
    inca = (inc + K['fee']) / eby; elah = elh / eby
    pdba = inca / (1 - K['rce'])                     # simplified rate-based approximation
    pdbe = bisect(lambda x: el_gap(x, C, K), 0.001, 2.0, 100)               # solved, undiscounted
    pdbd = bisect(lambda x: el_gap(x, C, K, True), 0.001, 2.0, 100)         # solved, discounted at SOFR
    cps = K['cpn'] - K['rf5']; elUb = hm * (1 - rUb); elUd = hm * (1 - rUd)
    return {'eby': eby, 'elsh': elh, 'elsm': elm, 'elah': elah, 'elam': elm / eby, 'inca': inca,
            'neth': inca - elah, 'lry': K['sofr'] + inca - elah, 'pvr': (pvi + K['fee']) / pve,
            'pdba5': 1 - math.exp(-5 * pdba), 'pdbe': pdbe, 'pdbe5': 1 - math.exp(-5 * pdbe),
            'pdbd': pdbd, 'pdbd5': 1 - math.exp(-5 * pdbd), 'cps': cps, 'elUb': elUb, 'elUd': elUd,
            'pxb': price_30360(K['cpn'], K['rf5'] + elUb), 'pxd': price_30360(K['cpn'], K['rf5'] + elUd)}

if __name__ == '__main__':
    base = run(BASE); mult = market_multiple()
    print(f"Cost of equity {base['ke']:.4%}  WACC {base['wacc']:.4%}  diluted shares {base['N']:.1f} m  exit multiple {mult:.2f}x")
    print(f"{'Case':<9}{'EV':>9}{'ND 2026':>9}{'Val/sh':>8}{'Raw':>9}{'M2':>8}{'M3':>8}{'Return':>9}{'MinDSCR':>8}{'Unfund':>8}{'WfDate':>8}{'Unsec':>7}{'CCAC IV':>8}")
    for name, p in (('Base', BASE), ('Upside', UP), ('Downside', DOWN)):
        o = run(p)
        print(f"{name:<9}{o['ev']:>9,.0f}{o['nd26']:>9,.0f}{o['ps']:>8.2f}{o['v_raw']:>9.2f}{o['m2']:>8.2f}"
              f"{method3(o, mult):>8.2f}{o['ret']:>9.1%}{o['mindscr']:>8.2f}{o['unfunded']:>8,.0f}{o['dyear']:>8}{o['recU']:>7.0%}{o['recIV']:>8.0%}")
        print(f"          shares sold {o['iss']:,.0f} (new shares {o['newsh']:.1f} m); 2031 price {o['p31']:.2f} with capped calls, "
              f"{o['p31nc']:.2f} without; CCAC IV exposure at default {o['IVt']:,.0f}")
    print("\nBase case by year")
    for r in base['rows']:
        print(f"  {r['y']} revenue {r['rev']:>8,.0f} EBITDA {r['ebitda']:>8,.0f} capex {r['capex']:>7,.0f}"
              f" FCFF {r['fcff']:>7,.0f} interest {r['intr']:>6,.0f} DSCR {r['dscr']:.2f} net debt {r['nd']:>8,.0f}")
    print("\nSensitivity (one change from base): value per share before the zero floor")
    for name, ch in SENS:
        o = run({**BASE, **ch})
        print(f"  {name:<26}{o['v_raw']:>9.2f}  min DSCR {o['mindscr']:.2f}  funding need {o['cumneed']:>8,.0f}")
    print("\nBreak-even inputs")
    print(f"  EBITDA margin for value = market price       {be1:.4%}")
    print(f"  EBITDA margin for equity value = 0           {be2:.4%}")
    print(f"  Delivery delay for 2027 DSCR = 1.00x         {be3:.2f} months")
    print(f"  EBITDA margin for full unsecured recovery    {be4:.4%}")
    print(f"  Capital intensity for equity value = 0       {be5:.4f}")
    print(f"  Delivery delay for a first unfunded gap      {be6:.2f} months")
    print(f"\n2026 bridge: H2 deployment {base['h2dep']:,.0f}, H2 cash {base['h2cash']:,.0f}, paid in 2027 {base['defer']:,.0f}")
    cc = credit_check()
    print(f"Credit check: spread income {cc['inca']:.4%}, expected loss {cc['elah']:.4%}, "
          f"expected-value break-even five-year default {cc['pdbe5']:.1%} (discounted {cc['pdbd5']:.1%}; simplified approximation {cc['pdba5']:.1%}), note price at base EL spread {cc['pxb']:.2f}, at downside EL spread {cc['pxd']:.2f}")
