"""
H2 (Phase 3h): Monte Carlo over drilling success rate for the
Vienna Basin 40-doublet vision.

Question: how does a realistic dry-well rate change the geothermal LCOH?
The T5 sensitivity table uses "Geo CapEx +50% (dry-well premium)" as a
financial markup; this script replaces it with a proper probabilistic
model.

Method: Monte Carlo over the 40-doublet target. Each doublet attempt
requires two wells (production + injection). Per-well success
probability p is the main lever. Failed wells cost their full drilling
expense but produce nothing; successful doublets produce 140 GWh/yr at
the F2-frozen 18.8 MW_th and CF=0.85.

Probability assumptions:
  * Aderklaa-96 first-result temperature met expectations -> p ~0.8-0.9
  * Bavarian Molasse Basin empirical success rate ~0.7-0.85 (Agemar 2014)
  * Hauptdolomit fracture-control raises variance: we sweep p in
    {0.6, 0.75, 0.85, 0.9}.

Stdlib only.
"""

import random
import statistics

random.seed(42)


# %% [Inputs]

N_TARGET_DOUBLETS = 40
WELL_CAPEX_MEUR = 13.0       # one well: ~13 M EUR (half of doublet 26 M)
SURFACE_CAPEX_MEUR = 5.0     # per doublet, surface plant + connection
OPEX_PCT = 0.025
LIFETIME_YR = 30
DISCOUNT_RATE = 0.05
DOUBLET_HEAT_GWh_YR = 140    # frozen
N_TRIALS = 10000


def crf(r, n):
    return r * (1 + r)**n / ((1 + r)**n - 1)


CRF = crf(DISCOUNT_RATE, LIFETIME_YR)


# %% [Per-trial Monte Carlo]

def simulate_one_program(p_success_per_well, n_target):
    """Drill until n_target *operating* doublets are built.

    Strategy: drill doublet attempt; if production well fails, abandon
    that attempt; if injection well fails after production succeeded,
    retry injector once. Cost realised per attempt:
      both succeed       -> 2 * WELL_CAPEX + SURFACE_CAPEX
      first fails        -> 1 * WELL_CAPEX (no surface plant built)
      first OK, 2nd fails-> 2 * WELL_CAPEX (try once); if 3rd also fails:
                            3 * WELL_CAPEX + SURFACE_CAPEX (then accept the
                            loss; the production well counts as an
                            observation well and is decommissioned later).
    """
    n_built = 0
    total_capex = 0.0
    attempts = 0
    while n_built < n_target and attempts < n_target * 10:
        attempts += 1
        # Production well
        if random.random() < p_success_per_well:
            total_capex += WELL_CAPEX_MEUR
            # Injection well, with one retry
            injector_ok = False
            for _ in range(2):
                total_capex += WELL_CAPEX_MEUR
                if random.random() < p_success_per_well:
                    injector_ok = True
                    break
            if injector_ok:
                total_capex += SURFACE_CAPEX_MEUR
                n_built += 1
            else:
                # gave up after 2 injector tries -- production well becomes obs.
                pass
        else:
            total_capex += WELL_CAPEX_MEUR  # producer dry, abandon attempt
    return n_built, total_capex, attempts


def lcoh_from_program(n_built, total_capex_MEUR):
    """Compute LCOH given total program CapEx and number of operating
    doublets."""
    if n_built == 0:
        return float("inf")
    ann_capex = total_capex_MEUR * CRF
    ann_opex_fix = total_capex_MEUR * OPEX_PCT
    total_ann_cost_MEUR = ann_capex + ann_opex_fix
    annual_heat_MWh = n_built * DOUBLET_HEAT_GWh_YR * 1000
    return total_ann_cost_MEUR * 1e6 / annual_heat_MWh


# %% [Run]

print(f"=== Monte Carlo dry-well sensitivity (N={N_TRIALS} trials) ===")
print(f"Target: build {N_TARGET_DOUBLETS} operating doublets.")
print(f"Per-doublet baseline (no failure): "
      f"{2*WELL_CAPEX_MEUR + SURFACE_CAPEX_MEUR:.0f} M EUR.")
print()
print(f"  {'p_well':>7}  {'mean CapEx [M EUR]':>20}  "
      f"{'effective CapEx/doublet [M]':>30}  "
      f"{'LCOH p10 / p50 / p90 [EUR/MWh]':>35}")

for p in (0.6, 0.75, 0.85, 0.9):
    capex_samples = []
    lcoh_samples = []
    for _ in range(N_TRIALS):
        n_built, capex, _ = simulate_one_program(p, N_TARGET_DOUBLETS)
        capex_samples.append(capex)
        lcoh_samples.append(lcoh_from_program(n_built, capex))
    mean_capex = statistics.mean(capex_samples)
    eff_per_doublet = mean_capex / N_TARGET_DOUBLETS
    p10, p50, p90 = statistics.quantiles(lcoh_samples, n=10)[0], \
                    statistics.median(lcoh_samples), \
                    statistics.quantiles(lcoh_samples, n=10)[8]
    print(f"  {p:>7.2f}  {mean_capex:>20.0f}  {eff_per_doublet:>30.1f}  "
          f"{p10:>10.2f} / {p50:>5.2f} / {p90:>5.2f}")

print()


# %% [Interpretation]

print("Interpretation:")
print("  * p=0.90 (Aderklaa-96-like best case) keeps LCOH median ~21 EUR/MWh")
print("  * p=0.75 (Bavarian Molasse Basin published average) median ~24")
print("  * p=0.60 (pessimistic Hauptdolomit fracture-control scenario)")
print("    median ~33 -- in the range of T5's 'Geo OpEx 5%' or 'CF 0.70' rows.")
print("  * The full p90 LCOH at p=0.6 is ~38, still well below the HP base")
print("    case (67) and even the HP-2025-HP-weighted (74) -- the geo:HP")
print("    advantage survives even under pessimistic drilling assumptions.")
print("  * The T5 \"+50% CapEx dry-well premium\" sensitivity (LCOH 25.4)")
print("    corresponds approximately to p=0.85 in this MC model.")
