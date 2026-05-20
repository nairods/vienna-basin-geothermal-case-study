"""
Thread 7 (Phase 3d) --- Multi-doublet thermal interference for a
40-doublet Vienna Basin deployment.

The basic physics:
  * Each doublet's injector creates a cold thermal halo that grows over
    time. From mass-conservation + (rho c)_water / (rho c)_bulk:

        V_cooled(t) = Q t (rho c)_water / (rho c)_bulk

    Treating the halo as a cylinder of aquifer thickness h:

        r_halo(t) = sqrt( V_cooled / (pi h) )

  * Two doublets interact thermally when their halos touch:
    2 * r_halo(t_int) = D, where D is the inter-doublet distance.

  * Cumulative cooled basin volume = N * V_cooled(t)  (Halos do not
    overlap appreciably while D >> 2 r_halo.)

This model is conduction-light: heat diffusion away from the halo is
~30 m at 30 yr (thermal diffusivity ~1e-6 m^2/s), much less than the
advection-driven halo (~600 m), so the conduction blur is negligible
at the deployment scale.

Pressure interference is also considered separately because pressure
diffusivity is much larger than thermal --- but pressure fields from a
doublet form a *dipole* at large distance, so the net pressure
perturbation falls as 1/D^2, much faster than a single well's 1/ln(D).

Stdlib only.
"""

import math

# %% [Frozen inputs --- same as F1 / t7_breakthrough.py]

# Reservoir
PHI = 0.20
RHOC_WATER = 4.18e6
RHOC_ROCK = 2.20e6
RHOC_BULK = PHI * RHOC_WATER + (1 - PHI) * RHOC_ROCK   # 2.60e6 J/(m^3 K)
H_AQUIFER = 100.0            # m
Q_PER_DOUBLET = 0.075        # m^3/s (75 kg/s)

# Deployment
N_DOUBLETS = 40
DEPLOYMENT_AREA_KM2 = 1500.0   # central Vienna Basin target area
DEPLOYMENT_LIFETIME_YR = 30.0


# %% [Halo growth]

def halo_radius_m(t_s: float, h: float = H_AQUIFER,
                  Q: float = Q_PER_DOUBLET) -> float:
    """Cylindrical halo radius of cooled rock around a single injector."""
    V_cooled = Q * t_s * RHOC_WATER / RHOC_BULK
    return math.sqrt(V_cooled / (math.pi * h))


def interaction_time_yr(D_m: float, h: float = H_AQUIFER,
                         Q: float = Q_PER_DOUBLET) -> float:
    """Time at which two halos at separation D first touch (2 r_halo = D)."""
    # r_halo^2 = Q t (rho c)_w / (pi h (rho c)_b)
    # 2 r_halo = D --> r_halo = D/2 --> r_halo^2 = D^2/4
    t_s = math.pi * h * (D_m**2 / 4) * RHOC_BULK / (Q * RHOC_WATER)
    return t_s / (3600 * 24 * 365.25)


def s_per_yr(yr: float) -> float:
    return yr * 365.25 * 86400


# %% [Halo radius over time for the standard doublet]

print(f"=== Single-doublet halo radius (standard Aspern doublet) ===")
print(f"  {'t [yr]':>8}  {'r_halo [m]':>11}  {'V_cooled [10^7 m^3]':>22}")
for yr in (1, 5, 10, 20, 30, 50, 100):
    r = halo_radius_m(s_per_yr(yr))
    V = math.pi * r**2 * H_AQUIFER
    print(f"  {yr:>8d}  {r:>11.0f}  {V/1e7:>22.2f}")
print()


# %% [Deployment geometry --- hexagonal grid in 1500 km^2]

# Hex grid: a hex cell has area = (3 sqrt(3) / 2) * s^2 where s = edge length.
# For N doublets in area A, area per cell = A / N.
# Nearest-neighbor distance in hex grid = s.
A_m2 = DEPLOYMENT_AREA_KM2 * 1e6
area_per_cell = A_m2 / N_DOUBLETS
hex_edge_m = math.sqrt(2 * area_per_cell / (3 * math.sqrt(3)))
# Nearest-neighbor distance in a hex grid of edge length s is also s
# (each hex cell has 6 nearest neighbors at distance s).
d_NN_m = hex_edge_m
# Square-grid alternative for comparison
d_square_m = math.sqrt(area_per_cell)

print(f"=== Deployment geometry: {N_DOUBLETS} doublets in "
      f"{DEPLOYMENT_AREA_KM2:.0f} km^2 ===")
print(f"  Area per doublet:                          {area_per_cell/1e6:.1f} km^2")
print(f"  Hex-grid nearest-neighbour distance:       {d_NN_m/1000:.2f} km")
print(f"  Square-grid nearest-neighbour distance:    {d_square_m/1000:.2f} km")
print()


# %% [Interaction-time table for various NN distances]

print(f"=== Halo-interaction time vs. inter-doublet distance ===")
print(f"  {'D [km]':>8}  {'t_int [yr]':>12}  {'comment':<40}")
for D_km in (1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 10.0):
    t_int = interaction_time_yr(D_km * 1000)
    comment = ""
    if t_int < 30:
        comment = "INTERACTION WITHIN PLANT LIFETIME"
    elif t_int < 60:
        comment = "interaction within ~2x plant lifetime"
    else:
        comment = "safely separated for 30-yr operation"
    print(f"  {D_km:>8.1f}  {t_int:>12.0f}  {comment:<40}")
print()

# Critical-spacing inverse: at t=30 yr, what is r_halo? Halos touch
# when 2 r_halo = D, so critical separation = 2 r_halo(30 yr).
r30 = halo_radius_m(s_per_yr(30))
d_crit_m = 2 * r30
print(f"=== Critical spacing for 30-yr operation ===")
print(f"  r_halo at 30 yr:               {r30:.0f} m")
print(f"  Critical doublet separation:   {d_crit_m:.0f} m "
      f"({d_crit_m/1000:.2f} km)")
print(f"  Our {N_DOUBLETS}-doublet hex spacing:        "
      f"{d_NN_m:.0f} m ({d_NN_m/1000:.2f} km)")
print(f"  Safety factor: {d_NN_m/d_crit_m:.1f}x  "
      f"({'SAFE' if d_NN_m > d_crit_m else 'OVERLAP'})")
print()


# %% [Cumulative basin cooling]

print(f"=== Cumulative cooled fraction of basin (no halo overlap regime) ===")
basin_volume_m3 = A_m2 * H_AQUIFER
print(f"  Basin target volume (1500 km^2 x 100 m):  "
      f"{basin_volume_m3/1e9:.0f} km^3 = {basin_volume_m3:.2e} m^3")
print(f"  {'t [yr]':>8}  {'V_cool_total [10^9 m^3]':>25}  "
      f"{'% of basin volume':>20}")
for yr in (1, 5, 10, 20, 30, 50, 100):
    V_per = Q_PER_DOUBLET * s_per_yr(yr) * RHOC_WATER / RHOC_BULK
    V_total = N_DOUBLETS * V_per
    frac = V_total / basin_volume_m3 * 100
    print(f"  {yr:>8d}  {V_total/1e9:>25.3f}  {frac:>20.3f}")
print()


# %% [Maximum number of doublets without interference]

print(f"=== How many doublets fit at 30-yr no-interference? ===")
# critical separation d_crit; hex-grid density: area per cell = d_crit^2 *
# sqrt(3)/2 (since hex edge = NN distance = d_crit)
area_per_cell_crit = d_crit_m**2 * math.sqrt(3) / 2
N_max = int(A_m2 // area_per_cell_crit)
print(f"  Area per cell at d_NN = d_crit ({d_crit_m:.0f} m): "
      f"{area_per_cell_crit/1e6:.2f} km^2")
print(f"  Maximum doublets in 1500 km^2 without 30-yr interference: "
      f"~{N_max}")
print(f"  This is the geometric upper bound on Vienna Basin geothermal")
print(f"  deployment density --- well above any plausible utility target.")
print()


# %% [Pressure interference --- order-of-magnitude]

print(f"=== Pressure interference: a different physics ===")
print(f"  Hydraulic diffusivity D_h for a typical sedimentary aquifer:")
print(f"    ~1 m^2/s (vs. thermal diffusivity ~1e-6 m^2/s).")
print(f"  Pressure-front propagation in 30 yr: sqrt(D_h t) ~ "
      f"{math.sqrt(1.0 * s_per_yr(30))/1000:.0f} km --- reaches basin scale.")
print(f"  BUT: doublet pressure field is a dipole (producer + injector),")
print(f"  so net pressure perturbation at distance D >> L falls as ~1/D^2,")
print(f"  not as ln(D) (single well). Net far-field pressure interference")
print(f"  between doublets is therefore much weaker than the thermal case")
print(f"  suggests at first glance.")
print(f"  Order-of-magnitude: at 6 km from a doublet with L=1.5 km spacing,")
print(f"  net dipole pressure ~ (Q mu / (2 pi k h)) * (L^2 / D^2)")
mu = 2.8e-4         # Pa s, water at ~100 C
k = 1e-13           # m^2, mid-range Aderklaa Conglomerate permeability
L = 1500.0          # m, intra-doublet spacing
D = 6000.0          # m, inter-doublet
dp_dipole = (Q_PER_DOUBLET * mu / (2 * math.pi * k * H_AQUIFER)) * \
            (L**2 / D**2)
print(f"    -> Delta p ~ {dp_dipole/1e6:.2f} MPa per neighbour at 6 km.")
print(f"    With 6 hex-grid neighbours superposed (order of magnitude),")
print(f"    additive pressure could reach a few MPa --- comparable to the")
print(f"    Coulomb-stress estimate in T2 but still well within the")
print(f"    operational envelope.")
print()


# %% [Implication for T2 traffic-light radius]

print(f"=== Implication for T2 traffic-light radius ===")
print(f"  Thermal halos at 30 yr:  r = {r30:.0f} m  (small, localized)")
print(f"  Pressure perturbation:   km-scale; depends on doublet design")
print(f"  Recommended T2 monitoring radius around each plant: 10 km")
print(f"  (already in the Phase 2b traffic-light proposal).")
print(f"  Multi-doublet superposition at hex-grid {d_NN_m/1000:.1f} km spacing:")
print(f"  thermal interference is NEGLIGIBLE for plant-lifetime horizons.")
