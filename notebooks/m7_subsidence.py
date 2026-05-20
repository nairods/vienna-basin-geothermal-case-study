"""
M7 (Phase 3h): InSAR-scale surface subsidence from thermo-elastic
contraction of the cooled reservoir volume at Aspern.

Physics: when an aquifer cools by Delta_T, its rock matrix contracts by
linear strain alpha*Delta_T. For a cooled column of thickness h, the
vertical compaction at the cooled depth is h * alpha * Delta_T. Surface
subsidence is the integrated vertical compaction transmitted through
the overburden; for a localised cooled volume at depth D, the surface
signal is attenuated by a factor related to (h/D) and the Poisson ratio
(Geertsma nucleus-of-strain solution).

We compute (a) the simple uniform-compaction bound, (b) a Geertsma-like
disc-shaped source approximation, and (c) the full-basin 40-doublet
cumulative signal.

Stdlib only.
"""

import math


# %% [Inputs --- consistent with T7]

ALPHA_LIN = 1e-5          # /K, linear thermal expansion (sedimentary rock)
DELTA_T = 60.0            # K, cold-front temperature drop
H_AQUIFER = 100.0         # m, aquifer thickness
DEPTH = 2900.0            # m, reservoir depth
R_HALO_30YR = 603.0       # m, halo radius at 30 yr (from t7_multidoublet.py)
NU = 0.25                 # Poisson's ratio
N_DOUBLETS = 40
DEPLOYMENT_AREA_KM2 = 1500.0


# %% [Method (a): uniform-compaction upper bound directly above a doublet]

# Vertical strain in the cooled aquifer:
eps_z = ALPHA_LIN * DELTA_T
# Vertical compaction of the cooled column = h * eps_z:
delta_h = H_AQUIFER * eps_z  # metres, 30-yr cumulative

print(f"=== Surface subsidence directly above an Aspern doublet ===")
print(f"  Linear thermal strain (alpha*dT): {eps_z*1000:.3f} mm/m")
print(f"  Cooled-column vertical compaction (h=100m, dT=60K, 30yr):")
print(f"    {delta_h*1000:.0f} mm = {delta_h*1000/30:.1f} mm/yr")
print()


# %% [Method (b): Geertsma disc source attenuation factor]

# For a thin disc-shaped reservoir compaction source of radius R and
# thickness h at depth D, the vertical surface displacement directly
# above the disc centre is:
#   u_z(0) = -2 * (1 - nu) * eps_v * h * [1 - D / sqrt(D^2 + R^2)]
# where eps_v = 3 * alpha * dT for volumetric (or eps_z * (1 + 2*nu/(1-nu))
# for the equivalent isotropic case). For a thin reservoir, the limit
# R >> D gives ~2(1-nu)*eps_v*h; R << D gives a much smaller surface
# signal.

eps_v = 3 * ALPHA_LIN * DELTA_T   # volumetric strain
R = R_HALO_30YR
D = DEPTH

# Surface vertical displacement (negative = down, here we report magnitude)
geertsma_factor = 1 - D / math.sqrt(D**2 + R**2)
u_z_surface = 2 * (1 - NU) * eps_v * H_AQUIFER * geertsma_factor

print(f"=== Method (b): Geertsma disc-source surface estimate ===")
print(f"  Volumetric strain (3*alpha*dT): {eps_v*1000:.3f} mm/m")
print(f"  R/D ratio: {R/D:.2f} (halo radius / depth)")
print(f"  Geertsma attenuation factor [1 - D/sqrt(D^2+R^2)]: {geertsma_factor:.4f}")
print(f"  Surface subsidence directly above doublet centre:")
print(f"    {u_z_surface*1000:.1f} mm cumulative over 30 yr "
      f"= {u_z_surface*1000/30:.2f} mm/yr")
print()


# %% [Method (c): basin-wide superposition with correct off-axis attenuation]

# At lateral distance r from a point source at depth D with total
# volume change Delta_V, the vertical surface displacement is
#   u_z(r) ~= - Delta_V * D / (2 pi (D^2 + r^2)^{3/2})    (Mogi-like)
# This is the correct asymptotic far-field. For our case:
#   Delta_V_per_doublet = V_cooled * eps_v = (pi R_halo^2 h) * (3 alpha dT)

V_cooled_per_doublet = math.pi * R_HALO_30YR**2 * H_AQUIFER
DeltaV = V_cooled_per_doublet * eps_v   # m^3 of contraction per doublet

def u_z_offaxis(r_lateral, D_depth, DeltaV):
    return DeltaV * D_depth / (2 * math.pi * (D_depth**2 + r_lateral**2)**1.5)

u_z_neighbour = u_z_offaxis(3800.0, D, DeltaV)

print(f"=== Method (c): basin-scale superposition ===")
print(f"  Volume contraction per doublet: Delta_V = "
      f"{DeltaV:.1f} m^3 cumulative over 30 yr")
print(f"  Off-axis (Mogi-style) per neighbour at 3.8 km lateral:")
print(f"    {u_z_neighbour*1000:.3f} mm cum.  ({u_z_neighbour*1000/30:.4f} mm/yr)")
print(f"  Local (above own doublet, Geertsma): {u_z_surface*1000:.1f} mm cum.")
print(f"  6 hex-grid neighbours superposed: {6*u_z_neighbour*1000:.3f} mm")
total_local = u_z_surface + 6 * u_z_neighbour
print(f"  Total surface subsidence at a doublet location:")
print(f"    ~{total_local*1000:.1f} mm cum.  = ~{total_local*1000/30:.2f} mm/yr")
print(f"  (Neighbour contributions roughly double the local signal at hex-grid")
print(f"   spacing; the rate is still ~half the 1 mm/yr InSAR detection limit.)")
print()

# %% [Comparison to InSAR detectability and damage thresholds]

print(f"=== Detectability and damage thresholds ===")
print(f"  Sentinel-1 InSAR long-time-series detection limit: ~1 mm/yr")
print(f"  C-band InSAR seasonal accuracy: ~5 mm vertical")
print(f"  Damage threshold (urban masonry): typically 2-5 mm/yr sustained")
print(f"  Surface tilting threshold (services/utilities): ~1 mm/m total")
print()

local_mm_yr = u_z_surface * 1000 / 30
print(f"  Local rate at Aspern doublet: ~{local_mm_yr:.2f} mm/yr")
if local_mm_yr < 1:
    print("  -> BELOW InSAR detection limit; sub-millimetre signal.")
elif local_mm_yr < 2:
    print("  -> AT InSAR detection limit; would show in long time series but")
    print("     well below structural damage thresholds.")
elif local_mm_yr < 5:
    print("  -> DETECTABLE by InSAR. Below damage threshold but politically")
    print("     visible. Monitoring recommended.")
else:
    print("  -> SIGNIFICANT. Would require structural assessment.")
print()


# %% [Operational implication]

print(f"=== Operational implication for the Aspern programme ===")
print(f"  The cooled-volume thermo-elastic surface signal at Aspern is")
print(f"  modelled here as ~{local_mm_yr:.1f} mm/yr at the doublet centre,")
print(f"  declining rapidly with lateral distance. This sits at or below")
print(f"  the InSAR detection threshold and is well below structural")
print(f"  damage limits, but:")
print(f"")
print(f"  (1) Sentinel-1 baseline observations are already public for")
print(f"      Donaustadt; a 30-yr cumulative signal of {u_z_surface*1000:.0f} mm")
print(f"      would be statistically robust against background ground")
print(f"      motion (~1-2 mm/yr from natural compaction).")
print(f"  (2) The signal IS centred on the doublet, which makes")
print(f"      attribution unambiguous if local InSAR is recorded.")
print(f"  (3) Differential subsidence between doublet centre and nearest")
print(f"      neighbour at 3.8 km is ~{(u_z_surface - u_z_far_per_doublet)*1000:.0f} mm; well below the")
print(f"      tilt damage threshold for adjacent buildings.")
print(f"")
print(f"  Conclusion: subsidence is a *monitoring* obligation, not a")
print(f"  showstopper or major design constraint, for the Vienna Basin")
print(f"  40-doublet vision at the proposed deployment density.")
