r"""
Thread 4 --- Doublet count vs.\ seasonal storage volume for Vienna DH.

Implements the two-block seasonal energy balance from project.tex
thread 4 and reproduces the headline numbers and sensitivity table.

Stdlib only. Cells delimited by `# %%`.
"""

# %% [Frozen inputs from project.tex F1/F2 + thread 4]

# Demand (two-block seasonal split)
ANNUAL_DEMAND_GWh = 6000.0       # F2 frozen
D_w_MW = 1000.0                  # winter half avg [MW] (Q1+Q4)
D_s_MW = 370.0                   # summer half avg [MW] (Q2+Q3)
SEASON_HOURS = 4380              # half-year [h]
PEAK_HISTORICAL_MW = 2308.0      # documented historical peak [43]
SUMMER_TROUGH_MW = 300.0         # F2

# Doublet
P_DOUBLET_MW = 18.8              # F2 frozen
CF_DOUBLET = 0.85                # frozen
P_EFF_PER_DOUBLET_MW = P_DOUBLET_MW * CF_DOUBLET    # continuous effective output

# Storage
ETA_RTE_BASE = 0.70              # round-trip efficiency
DELTA_T_BASE = 60.0              # storage temperature lift [K]
RHO_WATER = 1000.0               # kg/m^3
CP_WATER = 4180.0                # J/(kg K)

HOURS_PER_YR = 8760


# %% [Sanity check: two-block seasonal split fits annual total]

annual_check_GWh = (D_w_MW + D_s_MW) * SEASON_HOURS * 2 / 2000.0  # GWh
# Each half: D_avg * 4380 h, in MW*h => /1000 = GWh; sum two halves
# But (D_w + D_s) covers two halves once each, so /2 to fix; rewrite cleanly:
annual_check_GWh = (D_w_MW * SEASON_HOURS + D_s_MW * SEASON_HOURS) / 1000.0
print(f"[sanity] two-block annual integral = {annual_check_GWh:.0f} GWh "
      f"(target {ANNUAL_DEMAND_GWh:.0f})")
print()


# %% [Energy-balance optimisation]

def doublets_with_storage(D_w: float, D_s: float, P_eff: float,
                          eta: float) -> float:
    """N >= (D_w + eta*D_s) / (P_eff * (1+eta)).  See project.tex T4 derivation."""
    return (D_w + eta * D_s) / (P_eff * (1 + eta))


def storage_volume_m3(P_eff: float, N: int, D_s: float, season_h: float,
                      delta_T: float) -> float:
    """Stored summer-surplus energy converted to water-equivalent volume."""
    surplus_MW = P_eff * N - D_s
    if surplus_MW <= 0:
        return 0.0
    energy_MWh = surplus_MW * season_h
    energy_J = energy_MWh * 3.6e9                  # 1 MWh = 3.6e9 J
    return energy_J / (RHO_WATER * CP_WATER * delta_T)


N_base = doublets_with_storage(D_w_MW, D_s_MW, P_EFF_PER_DOUBLET_MW,
                               ETA_RTE_BASE)
V_base = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N_base, D_s_MW,
                           SEASON_HOURS, DELTA_T_BASE)
print(f"=== Base case (eta=0.70, deltaT=60K) ===")
print(f"  N required             = {N_base:.1f} doublets")
print(f"  Storage volume         = {V_base/1e6:.1f} million m^3")
print(f"  Surplus per summer     = "
      f"{(P_EFF_PER_DOUBLET_MW * N_base - D_s_MW) * SEASON_HOURS / 1000:.0f} GWh")
print()


# %% [No-storage baseline]

# Without storage: need P_eff*N >= D_w (winter average)
N_no_storage_winter_avg = D_w_MW / P_EFF_PER_DOUBLET_MW
# To meet winter peak (historical 2308 MW, allowing say 70% covered by geo,
# 30% by other peakers):
peak_target_MW = 0.70 * PEAK_HISTORICAL_MW
N_no_storage_peak = peak_target_MW / P_DOUBLET_MW   # peak power, not effective
N_full_coverage_energy = ANNUAL_DEMAND_GWh * 1000.0 / \
                         (P_DOUBLET_MW * HOURS_PER_YR * CF_DOUBLET)

print(f"=== No-storage baselines ===")
print(f"  N to meet winter avg alone        = {N_no_storage_winter_avg:.1f}")
print(f"  N to cover 70% of historical peak = {N_no_storage_peak:.1f}")
print(f"  N for full annual coverage (CF .85, no storage) = "
      f"{N_full_coverage_energy:.1f}")
print()


# %% [Sensitivity table]

print(f"=== Sensitivity table ===")
print(f"  {'Perturbation':<45} {'N':>6} {'V (10^6 m^3)':>12}")

# Base
N = doublets_with_storage(D_w_MW, D_s_MW, P_EFF_PER_DOUBLET_MW, 0.70)
V = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N, D_s_MW, SEASON_HOURS, 60)
print(f"  {'Base (eta=0.70, deltaT=60K)':<45} {N:>6.1f} {V/1e6:>12.1f}")

# eta = 0.5
N = doublets_with_storage(D_w_MW, D_s_MW, P_EFF_PER_DOUBLET_MW, 0.50)
V = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N, D_s_MW, SEASON_HOURS, 60)
print(f"  {'eta = 0.50 (poor HT-ATES)':<45} {N:>6.1f} {V/1e6:>12.1f}")

# eta = 0.85
N = doublets_with_storage(D_w_MW, D_s_MW, P_EFF_PER_DOUBLET_MW, 0.85)
V = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N, D_s_MW, SEASON_HOURS, 60)
print(f"  {'eta = 0.85 (best HT-ATES)':<45} {N:>6.1f} {V/1e6:>12.1f}")

# deltaT = 30
N = doublets_with_storage(D_w_MW, D_s_MW, P_EFF_PER_DOUBLET_MW, 0.70)
V = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N, D_s_MW, SEASON_HOURS, 30)
print(f"  {'deltaT = 30 K (modest lift)':<45} {N:>6.1f} {V/1e6:>12.1f}")

# deltaT = 90
V = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N, D_s_MW, SEASON_HOURS, 90)
print(f"  {'deltaT = 90 K (steam-grade)':<45} {N:>6.1f} {V/1e6:>12.1f}")

# colder winter average
N = doublets_with_storage(1300.0, D_s_MW, P_EFF_PER_DOUBLET_MW, 0.70)
V = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N, D_s_MW, SEASON_HOURS, 60)
print(f"  {'Winter avg D_w = 1.3 GW (colder)':<45} {N:>6.1f} {V/1e6:>12.1f}")

# 60% coverage target
COVERAGE = 0.60
ann_target_GWh = COVERAGE * ANNUAL_DEMAND_GWh
N_60 = ann_target_GWh * 1000 / (P_DOUBLET_MW * HOURS_PER_YR * CF_DOUBLET)
# Storage needs less: roughly scale by coverage ratio
V_60_lo = storage_volume_m3(P_EFF_PER_DOUBLET_MW, N_60, D_s_MW,
                            SEASON_HOURS, 60) if P_EFF_PER_DOUBLET_MW * N_60 > D_s_MW else 0.0
print(f"  {'60% coverage target':<45} {N_60:>6.1f} ~{V_60_lo/1e6:>11.1f} (no-storage-loss bound)")
print()


# %% [Wien Energie roadmap cross-check]

# Stated targets:
#   ~120 MW_th by 2030  -> N = 120 / 18.8 = 6.4 doublets
#   ~4 TWh/yr by 2040   -> N at CF 0.85 = 4000 / 140 = 28.6 doublets
n_2030 = 120 / P_DOUBLET_MW
n_2040 = 4000 / (P_DOUBLET_MW * HOURS_PER_YR * CF_DOUBLET / 1000)
print(f"=== Wien Energie roadmap cross-check ===")
print(f"  120 MW by 2030      -> {n_2030:.1f} doublets")
print(f"  4 TWh/yr by 2040    -> {n_2040:.1f} doublets")
print(f"  Our 60% coverage    -> {N_60:.1f} doublets   (alignment is good)")
print()


# %% [Verification against project.tex headline values]

def assert_close(name, actual, expected, tol_pct=2.0):
    if expected == 0:
        ok = abs(actual) <= tol_pct
    else:
        ok = abs(actual - expected) / expected * 100 <= tol_pct
    tag = "OK" if ok else "MISMATCH"
    if expected != 0:
        diff_pct = abs(actual - expected) / expected * 100
        print(f"  [{tag}] {name}: actual {actual:.2f}, expected {expected:.2f}, "
              f"diff {diff_pct:.2f}%")
    else:
        print(f"  [{tag}] {name}: actual {actual:.2f}, expected {expected:.2f}")

print(f"=== Verification against project.tex ===")
assert_close("N base case", N_base, 46.0)
assert_close("V base case (10^6 m^3)", V_base / 1e6, 23.0)
assert_close("N_60 (60% coverage)", N_60, 25.7)
