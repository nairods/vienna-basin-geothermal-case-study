"""
Thread 7 --- Bodvarsson--Tsang analytical thermal-breakthrough estimate
for an Aspern-type doublet in the Aderklaa Conglomerate.

Reproduces the headline 62-yr breakthrough estimate and the sensitivity
table from project.tex thread 7. Includes the multi-doublet thermal
halo calculation and the thermo-elastic stress estimate that links to
thread 2.

Stdlib + math only.
"""

import math

# %% [Frozen inputs from project.tex F1 + thread 7]

# Reservoir (Aderklaa Conglomerate at Aspern)
L_BASE = 1500.0           # doublet spacing [m]
H_BASE = 100.0            # aquifer thickness [m]
PHI_BASE = 0.20           # porosity
RHOC_WATER = 4.18e6       # volumetric heat capacity of water [J/(m^3 K)]
RHOC_ROCK = 2.20e6        # vol. heat capacity of bulk solid rock [J/(m^3 K)]
Q_BASE = 0.075            # volumetric flow rate [m^3/s] (75 kg/s @ 1000 kg/m^3)
GEOM_FACTOR = 3.0         # streamline geometry correction (Bodvarsson-Tsang)

# Thermo-elastic constants (thread 2 link)
ALPHA = 1e-5              # linear thermal expansion [/K]
E_YOUNG = 30e9            # Young's modulus [Pa] (typical sedimentary)
NU = 0.25                 # Poisson's ratio
DELTA_T_COOLING = 60.0    # cold-front temperature drop [K]


# %% [Bodvarsson--Tsang formula]

def thermal_breakthrough_yr(L, h, Q, phi, rhoc_water=RHOC_WATER,
                             rhoc_rock=RHOC_ROCK, geom=GEOM_FACTOR):
    """t_TB ~ V_swept * (rho c)_bulk / (3 * (rho c)_water * Q)."""
    rhoc_bulk = phi * rhoc_water + (1 - phi) * rhoc_rock
    V_swept = math.pi * L**2 * h
    t_TB_seconds = V_swept * rhoc_bulk / (geom * rhoc_water * Q)
    return t_TB_seconds / (3600 * 24 * 365.25)


# %% [Base case]

t_base = thermal_breakthrough_yr(L_BASE, H_BASE, Q_BASE, PHI_BASE)
print(f"=== Base case Aspern doublet (Aderklaa Conglomerate) ===")
print(f"  L = {L_BASE:.0f} m, h = {H_BASE:.0f} m, "
      f"phi = {PHI_BASE:.2f}, Q = {Q_BASE:.3f} m^3/s")
rhoc_bulk = PHI_BASE * RHOC_WATER + (1 - PHI_BASE) * RHOC_ROCK
V_swept = math.pi * L_BASE**2 * H_BASE
print(f"  (rho c)_bulk = {rhoc_bulk/1e6:.2f} x 10^6 J/(m^3 K)")
print(f"  V_swept      = {V_swept/1e8:.2f} x 10^8 m^3")
print(f"  t_TB         = {t_base:.1f} yr")
print()


# %% [Sensitivity table]

print(f"=== Sensitivity table ===")
print(f"  {'Perturbation':<40} {'t_TB [yr]':>10}")

print(f"  {'Base (L=1500m, h=100m, Q=75kg/s)':<40} {t_base:>10.1f}")

# Closer spacing
t = thermal_breakthrough_yr(1000, H_BASE, Q_BASE, PHI_BASE)
print(f"  {'L = 1000 m (tighter spacing)':<40} {t:>10.1f}")

# Wider
t = thermal_breakthrough_yr(2000, H_BASE, Q_BASE, PHI_BASE)
print(f"  {'L = 2000 m (wider spacing)':<40} {t:>10.1f}")

# Thinner aquifer
t = thermal_breakthrough_yr(L_BASE, 50, Q_BASE, PHI_BASE)
print(f"  {'h = 50 m (thinner aquifer)':<40} {t:>10.1f}")

# Thicker aquifer
t = thermal_breakthrough_yr(L_BASE, 200, Q_BASE, PHI_BASE)
print(f"  {'h = 200 m (full Aderklaa interval)':<40} {t:>10.1f}")

# Higher flow rate
t = thermal_breakthrough_yr(L_BASE, H_BASE, 0.150, PHI_BASE)
print(f"  {'Q = 150 kg/s (higher production)':<40} {t:>10.1f}")

# Higher porosity
t = thermal_breakthrough_yr(L_BASE, H_BASE, Q_BASE, 0.30)
print(f"  {'phi = 0.30 (high porosity)':<40} {t:>10.1f}")

# Lower porosity
t = thermal_breakthrough_yr(L_BASE, H_BASE, Q_BASE, 0.10)
print(f"  {'phi = 0.10 (low porosity)':<40} {t:>10.1f}")

# Dogger comparison: L=1000, h=20 m (typical Dogger geometry)
t = thermal_breakthrough_yr(1000, 20, 0.060, 0.15)  # Dogger Q ~ 0.05--0.07
print(f"  {'Dogger comparison: L=1km, h=20m, Q=60':<40} {t:>10.1f}")
print()


# %% [Multi-doublet thermal halo at 30 yr]

# Cooled rock volume per doublet:
#   V_cool ~ (Q * t / (1 - phi)) * (rho c)_water / (rho c)_bulk
T_OP_YR = 30.0
t_op_s = T_OP_YR * 365.25 * 86400
rhoc_bulk = PHI_BASE * RHOC_WATER + (1 - PHI_BASE) * RHOC_ROCK
V_cool = (Q_BASE * t_op_s / (1 - PHI_BASE)) * (RHOC_WATER / rhoc_bulk)
# Thermal halo radius for cylinder of height h:
R_halo = math.sqrt(V_cool / (math.pi * H_BASE))

print(f"=== Multi-doublet thermal halo (30 yr) ===")
print(f"  Cooled volume per doublet: {V_cool/1e8:.2f} x 10^8 m^3")
print(f"  Equiv. cylindrical halo radius (h=100m): {R_halo:.0f} m")
print(f"  For 40 doublets in ~1500 km^2 Vienna Basin target area,")
print(f"  mean inter-doublet spacing = sqrt(1500/40) km ~ "
      f"{math.sqrt(1500.0/40.0):.1f} km")
print(f"  -> direct thermal interference NOT a first-order concern at 30 yr.")
print()


# %% [Thermo-elastic stress (links to thread 2)]

# Plane-strain thermal contraction stress within cooled region:
#   Delta_sigma = E * alpha * delta_T / (1 - nu)
sigma_thermal_MPa = E_YOUNG * ALPHA * DELTA_T_COOLING / (1 - NU) / 1e6
print(f"=== Thermo-elastic stress (link to T2) ===")
print(f"  Within cooled rock:")
print(f"  Delta_sigma = E*alpha*delta_T/(1-nu) "
      f"= {sigma_thermal_MPa:.1f} MPa (plane-strain estimate)")
print(f"  Order-of-magnitude transmitted stress at km-scale: "
      f"~{0.1:.1f}--{1.0:.1f} MPa (per Kivi et al. 2022)")
print(f"  This is at the empirical triggering threshold for")
print(f"  critically-stressed faults (~0.01--0.1 MPa).")
print()


# %% [Verification against project.tex]

EXPECTED_T_BASE = 62.0       # project.tex thread 7 headline

def assert_close(name, actual, expected, tol_pct=2.0):
    diff_pct = abs(actual - expected) / expected * 100
    tag = "OK" if diff_pct <= tol_pct else "MISMATCH"
    print(f"  [{tag}] {name}: actual {actual:.2f}, expected {expected:.2f}, "
          f"diff {diff_pct:.2f}%")

print(f"=== Verification against project.tex ===")
assert_close("t_TB base case [yr]", t_base, EXPECTED_T_BASE, tol_pct=3.0)
assert_close("Thermo-elastic stress [MPa]", sigma_thermal_MPa, 24.0, tol_pct=5.0)
