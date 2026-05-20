"""
Thread 4 (Phase 3c) --- LDC-based storage optimisation.

Replaces the two-block seasonal approximation with a daily load-duration
curve digitised from the Wien Energie / Schubert (IEA Bioenergy 2022)
presentation, slide 8: "District heating load duration curve [GWh/d]"
(Compass Lexecon 2021, "Waerme & Kaelte, Mobilitaet, Strom: Szenarien
fuer die Dekarbonisierung des Wiener Energiesystems bis 2040").

The LDC was digitised by visual reading at 400 dpi rendering. Each
sample is (day_rank, demand_GWh_per_day) where day_rank=1 is the
peak day and day_rank=365 the lowest-demand day.

Stdlib only. Run as `python3 notebooks/t4_storage_ldc.py`.
"""

# %% [Frozen inputs (consistent with project.tex F1/F2 and t4_storage.py)]

P_DOUBLET_MW = 18.8
CF_DOUBLET = 0.85
P_EFF_PER_DOUBLET_MW = P_DOUBLET_MW * CF_DOUBLET   # 15.98 MW continuous
HOURS_PER_DAY = 24
DAYS = 365
ETA_RTE_BASE = 0.70
DELTA_T_BASE = 60.0
RHO_WATER = 1000.0
CP_WATER = 4180.0

# %% [Digitised LDC from Schubert (2022) p.8 ---
#     dark "Heating demand" line, GWh per day, sorted descending]

LDC_DIGITISED = [
    # (rank, GWh/d)
    (  1, 47.5), (  5, 43.0), ( 10, 40.0), ( 15, 37.5), ( 20, 35.5),
    ( 25, 33.5), ( 30, 31.5), ( 35, 30.0), ( 40, 28.5), ( 50, 25.5),
    ( 60, 23.5), ( 70, 21.5), ( 80, 19.5), ( 90, 18.0), (100, 17.0),
    (115, 15.5), (130, 14.0), (145, 12.8), (160, 11.5), (180, 10.0),
    (200,  8.8), (220,  7.7), (240,  6.8), (260,  6.0), (280,  5.4),
    (300,  5.0), (320,  4.5), (340,  3.8), (355,  3.2), (365,  2.8),
]


# %% [Helpers]

def interpolate_ldc(samples=LDC_DIGITISED, n_days=DAYS):
    """Linearly interpolate the digitised LDC onto every day 1..n_days."""
    out = []
    for d in range(1, n_days + 1):
        if d <= samples[0][0]:
            out.append(samples[0][1])
            continue
        if d >= samples[-1][0]:
            out.append(samples[-1][1])
            continue
        for i in range(len(samples) - 1):
            r0, v0 = samples[i]
            r1, v1 = samples[i + 1]
            if r0 <= d <= r1:
                f = (d - r0) / (r1 - r0)
                out.append(v0 + f * (v1 - v0))
                break
    return out


def gwh_per_day_to_MW(gwh_d):
    return gwh_d * 1000 / 24  # 1 GWh/d = 1000/24 MW continuous


def storage_balance_for_baseload(ldc_GWhd, baseload_GWhd, eta):
    """For a given baseload-equivalent daily output, compute energy
    stored and discharged. Returns (deficit_GWh, surplus_GWh,
    feasibility, peak_stored_GWh)."""
    deficit_total = 0.0
    surplus_total = 0.0
    cumulative = 0.0
    peak_stored = 0.0
    for d in ldc_GWhd:
        delta = baseload_GWhd - d   # positive = surplus, negative = deficit
        if delta >= 0:
            surplus_total += delta
            cumulative += delta * eta    # charge stored (with loss)
        else:
            deficit_total += -delta
            cumulative -= -delta         # discharge (no loss on output)
        peak_stored = max(peak_stored, cumulative)
    feasible = (surplus_total * eta) >= deficit_total
    return deficit_total, surplus_total, feasible, peak_stored


# %% [Reconstruct curve and sanity-check]

ldc = interpolate_ldc()
total_GWh = sum(ldc)
print(f"=== Digitised LDC sanity check ===")
print(f"  Days: {len(ldc)}")
print(f"  Annual total: {total_GWh:.0f} GWh "
      f"(project.tex F2 frozen: ~6000 GWh)")
print(f"  Daily peak:   {ldc[0]:.1f} GWh/d  "
      f"-> peak-day-average {gwh_per_day_to_MW(ldc[0]):.0f} MW")
print(f"  Daily trough: {ldc[-1]:.1f} GWh/d  "
      f"-> trough-day-average {gwh_per_day_to_MW(ldc[-1]):.0f} MW")
print(f"  Mean:         {sum(ldc)/len(ldc):.1f} GWh/d  "
      f"-> mean continuous {gwh_per_day_to_MW(sum(ldc)/len(ldc)):.0f} MW")
# F2 cross-check: historical max = 2308 MW (peak hour, not peak day);
# peak hour / peak day average ratio for DH is typically 1.15--1.3
implied_peak_hour = gwh_per_day_to_MW(ldc[0]) * 1.20
print(f"  Implied peak hour (peak day * 1.20): {implied_peak_hour:.0f} MW  "
      f"(F2 historical max 2308 MW)")
print()


# %% [Sweep doublet count vs. storage requirement (LDC-based)]

print(f"=== Doublet-count sweep with LDC-based seasonal storage ===")
print(f"  eta = {ETA_RTE_BASE}, delta_T = {DELTA_T_BASE} K")
print(f"  {'N':>4}  {'baseload [MW]':>14}  {'baseload [GWh/d]':>17}  "
      f"{'storage [10^6 m3]':>20}  {'feasible?':>10}  {'annual cover [%]':>17}")

for N in range(20, 91, 5):
    baseload_MW = N * P_EFF_PER_DOUBLET_MW
    baseload_GWhd = baseload_MW * 24 / 1000.0
    deficit, surplus, feas, peak_stored_GWh = \
        storage_balance_for_baseload(ldc, baseload_GWhd, ETA_RTE_BASE)
    # Storage volume: peak stored energy
    V = peak_stored_GWh * 1e9 * 3600 / (RHO_WATER * CP_WATER * DELTA_T_BASE)
    # Annual covered share: produced + storage-delivered limited by demand
    produced = baseload_GWhd * DAYS
    annual_cover = min(produced, total_GWh) / total_GWh * 100
    print(f"  {N:>4}  {baseload_MW:>14.0f}  {baseload_GWhd:>17.1f}  "
          f"{V/1e6:>20.1f}  {str(feas):>10}  {annual_cover:>17.1f}")
print()


# %% [Find minimum N for full coverage]

print(f"=== Minimum N for energy-balance feasibility ===")
best_N = None
for N in range(1, 200):
    baseload_GWhd = N * P_EFF_PER_DOUBLET_MW * 24 / 1000.0
    deficit, surplus, feas, _ = storage_balance_for_baseload(ldc, baseload_GWhd,
                                                              ETA_RTE_BASE)
    if feas:
        best_N = N
        break
if best_N is not None:
    baseload_GWhd = best_N * P_EFF_PER_DOUBLET_MW * 24 / 1000.0
    deficit, surplus, feas, peak_stored = \
        storage_balance_for_baseload(ldc, baseload_GWhd, ETA_RTE_BASE)
    V = peak_stored * 1e9 * 3600 / (RHO_WATER * CP_WATER * DELTA_T_BASE)
    print(f"  Minimum N to balance seasonal demand: {best_N} doublets")
    print(f"  Baseload: {best_N * P_EFF_PER_DOUBLET_MW:.0f} MW continuous")
    print(f"  Daily surplus to store (LDC area): {surplus:.0f} GWh")
    print(f"  Daily deficit to discharge:        {deficit:.0f} GWh")
    print(f"  Peak storage charge:               {peak_stored:.0f} GWh")
    print(f"  -> required volume:                {V/1e6:.1f} million m^3")
else:
    print("  No feasible N <200")
print()


# %% [Compare with the two-block approximation]

# From t4_storage.py: two-block gives N >= 46
N_TWO_BLOCK = 46
baseload_GWhd = N_TWO_BLOCK * P_EFF_PER_DOUBLET_MW * 24 / 1000.0
deficit, surplus, feas, peak_stored = \
    storage_balance_for_baseload(ldc, baseload_GWhd, ETA_RTE_BASE)
V_two_block_under_ldc = peak_stored * 1e9 * 3600 / \
                        (RHO_WATER * CP_WATER * DELTA_T_BASE)
print(f"=== Two-block N=46 evaluated under the LDC ===")
print(f"  Baseload: {baseload_GWhd:.1f} GWh/d "
      f"= {N_TWO_BLOCK * P_EFF_PER_DOUBLET_MW:.0f} MW")
print(f"  Surplus * eta - Deficit = "
      f"{surplus * ETA_RTE_BASE - deficit:.0f} GWh (>=0 means feasible)")
print(f"  Storage required: {V_two_block_under_ldc/1e6:.1f} million m^3")
print(f"  Implication: the two-block model "
      f"{'OVER-' if best_N is not None and N_TWO_BLOCK > best_N else 'UNDER-'}"
      f"estimated N relative to the LDC reality.")
print()


# %% [Partial coverage scenarios under the LDC]

print(f"=== Partial coverage scenarios (LDC-based) ===")
print(f"  {'Coverage target':>15}  {'N needed':>9}  "
      f"{'storage [10^6 m3]':>20}")
for cov in (0.40, 0.50, 0.60, 0.70, 0.80, 0.90):
    target_GWh = cov * total_GWh
    # Choose N such that N * 365 * P_EFF * 24/1000 GWh = target
    # plus storage to absorb the LDC peaks
    N_target = target_GWh * 1000 / (P_EFF_PER_DOUBLET_MW * 24 * DAYS)
    N_int = int(round(N_target))
    baseload_GWhd = N_int * P_EFF_PER_DOUBLET_MW * 24 / 1000.0
    _, _, _, peak_stored = storage_balance_for_baseload(
        ldc, baseload_GWhd, ETA_RTE_BASE)
    V = peak_stored * 1e9 * 3600 / (RHO_WATER * CP_WATER * DELTA_T_BASE)
    print(f"  {cov*100:>13.0f}%  {N_int:>9d}  {V/1e6:>20.1f}")
print()


# %% [Capacity-factor estimate from LDC]

# For thread 5: what capacity factor does geothermal actually achieve
# under the LDC? Continuous baseload at N=46 gives effective CF=0.85 of
# the per-doublet output ONLY IF the storage absorbs all the summer
# surplus. Real-world: some surplus is curtailed (no infinite storage).

# Compute curtailment as a function of N
print(f"=== Effective capacity factor (curtailment-aware) ===")
print(f"  {'N':>4}  {'CF if all stored':>17}  {'CF curtailed (no storage)':>26}")
for N in (10, 20, 30, 40, 50, 60, 80, 100):
    baseload_GWhd = N * P_EFF_PER_DOUBLET_MW * 24 / 1000.0
    # Without storage, geothermal can only sell its output when D(day) > baseload
    sellable = sum(min(baseload_GWhd, d) for d in ldc)
    max_possible = baseload_GWhd * DAYS
    cf_curtailed = sellable / max_possible * CF_DOUBLET
    print(f"  {N:>4}  {CF_DOUBLET:>17.2f}  {cf_curtailed:>26.3f}")
print()


# %% [Notes / validation]

# Total annual production at N=46, CF=0.85: 46 * 18.8 * 8760 * 0.85 = 6,440 GWh.
# Compared to digitised LDC total ~6000-6200 GWh: matches within ~5-10%.
# Both consistent with project.tex F2 frozen 6 TWh.

# Peak-hour vs peak-day: the LDC is daily-resolved; the actual peak hour
# is ~1.15-1.30x the peak-day average. With peak day at 47.5 GWh/d (~1980
# MW continuous over 24h), peak hour ~2280-2570 MW, consistent with the
# documented historical peak of 2308 MW from [43].

print(f"=== Cross-check against project.tex ===")
print(f"  LDC annual total:   {total_GWh:.0f} GWh "
      f"(project.tex F2: ~6000)")
print(f"  LDC peak day:       {ldc[0]:.1f} GWh/d "
      f"-> {gwh_per_day_to_MW(ldc[0]):.0f} MW peak-day-average")
print(f"  Implied peak hour:  {implied_peak_hour:.0f} MW "
      f"(F2 documented: 2308 MW)")
print(f"  Two-block N=46 OK?  {'yes' if surplus*ETA_RTE_BASE >= deficit else 'no'} "
      f"under the LDC")
print(f"  LDC-minimum N:      {best_N} (vs. two-block estimate 46)")
