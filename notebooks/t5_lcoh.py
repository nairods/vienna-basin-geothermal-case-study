"""
Thread 5 --- Levelised cost of heat (LCOH) for deep geothermal vs.
large heat pump in the Vienna district-heating context.

Reproduces every number in project.tex thread 5 from the F1/F2/F3
frozen inputs. Stdlib only; no third-party dependencies.

Cells delimited by `# %%` are compatible with Jupyter (via jupytext)
and VS Code. The whole file also runs end-to-end as `python t5_lcoh.py`.
"""

# %% [Inputs --- frozen baseline from project.tex F1/F2/F3 + thread 5 table]

# Discount rate and lifetimes
r = 0.05                  # discount rate
n_geo = 30                # geothermal plant lifetime [yr]
n_hp = 20                 # heat pump plant lifetime [yr]

# Geothermal doublet
P_geo_MW = 18.8           # thermal power per doublet [MW_th] -- F2 frozen
CF_geo = 0.85             # capacity factor (frozen)
capex_geo_per_MW = 1.4    # CapEx per MW_th [million EUR/MW] -- F2
opex_geo_pct = 0.025      # fixed OpEx as fraction of CapEx per year

# Heat pump (Ebswien-type, 55 MW unit)
P_hp_MW = 55.0            # reference unit thermal power [MW_th]
CF_hp = 0.50              # capacity factor estimate (winter-leaning)
capex_hp_per_MW = 1.3     # CapEx per MW_th [million EUR/MW] -- ref [24]
opex_hp_pct = 0.05        # fixed OpEx as fraction of CapEx per year
cop_hp = 3.2              # average COP (wastewater source)
elec_price = 90.0         # base-case electricity wholesale [EUR/MWh] -- F3 mid

HOURS_PER_YR = 8760

# %% [Capital recovery factor (CRF)]

def crf(rate: float, lifetime: int) -> float:
    """Annuity factor for capital recovery."""
    if rate == 0:
        return 1.0 / lifetime
    return rate * (1 + rate)**lifetime / ((1 + rate)**lifetime - 1)


# %% [LCOH calculations]

def lcoh_geothermal(P_MW: float, CF: float,
                    capex_per_MW: float, opex_pct: float,
                    lifetime: int, rate: float) -> dict:
    """Return LCOH breakdown for a geothermal doublet."""
    capex = capex_per_MW * P_MW                        # million EUR
    ann_capex = capex * crf(rate, lifetime)            # million EUR/yr
    opex_fix = opex_pct * capex                        # million EUR/yr
    annual_heat_MWh = P_MW * HOURS_PER_YR * CF         # MWh/yr
    total_ann_cost = (ann_capex + opex_fix) * 1e6      # EUR/yr
    lcoh = total_ann_cost / annual_heat_MWh            # EUR/MWh_th
    return {
        "capex_MEUR": capex,
        "ann_capex_MEUR": ann_capex,
        "opex_fix_MEUR": opex_fix,
        "annual_heat_MWh": annual_heat_MWh,
        "total_ann_cost_MEUR": total_ann_cost / 1e6,
        "LCOH_EUR_per_MWh": lcoh,
    }


def lcoh_heatpump(P_MW: float, CF: float,
                  capex_per_MW: float, opex_pct: float,
                  cop: float, elec_price_per_MWh: float,
                  lifetime: int, rate: float) -> dict:
    """Return LCOH breakdown for a heat pump."""
    capex = capex_per_MW * P_MW                        # million EUR
    ann_capex = capex * crf(rate, lifetime)            # million EUR/yr
    opex_fix = opex_pct * capex                        # million EUR/yr
    annual_heat_MWh = P_MW * HOURS_PER_YR * CF         # MWh/yr
    elec_MWh = annual_heat_MWh / cop                   # MWh_e/yr
    opex_elec = elec_MWh * elec_price_per_MWh / 1e6    # million EUR/yr
    total_ann_cost = (ann_capex + opex_fix + opex_elec) * 1e6
    lcoh = total_ann_cost / annual_heat_MWh
    return {
        "capex_MEUR": capex,
        "ann_capex_MEUR": ann_capex,
        "opex_fix_MEUR": opex_fix,
        "opex_elec_MEUR": opex_elec,
        "elec_MWh": elec_MWh,
        "annual_heat_MWh": annual_heat_MWh,
        "total_ann_cost_MEUR": total_ann_cost / 1e6,
        "LCOH_EUR_per_MWh": lcoh,
    }


# %% [Base case]

geo_base = lcoh_geothermal(P_geo_MW, CF_geo, capex_geo_per_MW,
                           opex_geo_pct, n_geo, r)
hp_base = lcoh_heatpump(P_hp_MW, CF_hp, capex_hp_per_MW,
                        opex_hp_pct, cop_hp, elec_price, n_hp, r)

print("=== Base case ===")
print(f"  CRF_geo  = {crf(r, n_geo):.4f}")
print(f"  CRF_hp   = {crf(r, n_hp):.4f}")
print(f"  LCOH geo : {geo_base['LCOH_EUR_per_MWh']:7.2f} EUR/MWh_th"
      f"  (annual cost {geo_base['total_ann_cost_MEUR']:.2f} M, "
      f"heat {geo_base['annual_heat_MWh']:.0f} MWh)")
print(f"  LCOH HP  : {hp_base['LCOH_EUR_per_MWh']:7.2f} EUR/MWh_th"
      f"  (annual cost {hp_base['total_ann_cost_MEUR']:.2f} M, "
      f"heat {hp_base['annual_heat_MWh']:.0f} MWh)")
print(f"  Ratio HP/geo: {hp_base['LCOH_EUR_per_MWh'] / geo_base['LCOH_EUR_per_MWh']:.2f}x")
print()

# Expected from project.tex thread 5:
#   LCOH_geo ~ 17 EUR/MWh, LCOH_HP ~ 67 EUR/MWh, ratio ~ 4x


# %% [Sensitivity table --- single-parameter perturbations]

sens = []

# Geothermal perturbations
res = lcoh_geothermal(P_geo_MW, CF_geo, 1.5 * capex_geo_per_MW,
                      opex_geo_pct, n_geo, r)
sens.append(("Geo CapEx +50% (dry-well premium)", "geo",
             res["LCOH_EUR_per_MWh"]))

res = lcoh_geothermal(P_geo_MW, 0.70, capex_geo_per_MW,
                      opex_geo_pct, n_geo, r)
sens.append(("Geo CF -> 0.70 (well loss/depletion)", "geo",
             res["LCOH_EUR_per_MWh"]))

res = lcoh_geothermal(P_geo_MW, CF_geo, capex_geo_per_MW,
                      0.05, n_geo, r)
sens.append(("Geo OpEx -> 5%", "geo", res["LCOH_EUR_per_MWh"]))

# Heat pump perturbations
res = lcoh_heatpump(P_hp_MW, CF_hp, capex_hp_per_MW, opex_hp_pct,
                    cop_hp, 180.0, n_hp, r)
sens.append(("HP elec @ 180 EUR/MWh (winter peak pricing)", "hp",
             res["LCOH_EUR_per_MWh"]))

res = lcoh_heatpump(P_hp_MW, 0.30, capex_hp_per_MW, opex_hp_pct,
                    cop_hp, elec_price, n_hp, r)
sens.append(("HP CF -> 0.30 (peakier role)", "hp",
             res["LCOH_EUR_per_MWh"]))

res = lcoh_heatpump(P_hp_MW, CF_hp, capex_hp_per_MW, opex_hp_pct,
                    2.5, elec_price, n_hp, r)
sens.append(("HP COP -> 2.5 (older equipment)", "hp",
             res["LCOH_EUR_per_MWh"]))

# Worst-of-both combined
res_geo_worst = lcoh_geothermal(P_geo_MW, 0.70, 1.5 * capex_geo_per_MW,
                                0.05, n_geo, r)
res_hp_best = lcoh_heatpump(P_hp_MW, CF_hp, capex_hp_per_MW,
                            opex_hp_pct, cop_hp, 50.0, n_hp, r)
sens.append(("Worst-of-both: geo", "geo", res_geo_worst["LCOH_EUR_per_MWh"]))
sens.append(("Worst-of-both: HP", "hp", res_hp_best["LCOH_EUR_per_MWh"]))

print("=== Sensitivity table ===")
print(f"  {'Perturbation':<45} {'Tech':>4}  LCOH [EUR/MWh]")
for desc, tech, val in sens:
    print(f"  {desc:<45} {tech:>4}  {val:9.2f}")
print()


# %% [Carbon-intensity comparison --- thread 5 table]

# Heat-pump carbon intensity at given electricity grid intensity:
#   g CO2/kWh_th = (g CO2/kWh_e) / COP

scenarios = [
    ("Geothermal (deep DH, operational)",   None,   None),
    ("HP, Austrian grid 2024, op. 69 g/kWh", 69.0,  cop_hp),
    ("HP, Austrian grid 2024, life 106 g/kWh", 106.0, cop_hp),
    ("HP, winter peak 300 g/kWh (gas marginal)", 300.0, cop_hp),
    ("HP, winter peak 500 g/kWh (adverse import)", 500.0, cop_hp),
]

print("=== Carbon-intensity table (operational, per kWh_th) ===")
print(f"  {'Scenario':<48}  g CO2 / kWh_th")
for desc, grid_int, cop in scenarios:
    if grid_int is None:
        co2_per_kWh_th = 0.0
        note = "~0--5 (operational)"
        print(f"  {desc:<48}  {note}")
    else:
        co2_per_kWh_th = grid_int / cop
        print(f"  {desc:<48}  {co2_per_kWh_th:9.1f}")
print()


# %% [Break-even electricity price]

# At what wholesale electricity price would HP LCOH equal geo LCOH?
# Ignoring all other adjustments, solving for elec_price:
#   (ann_capex_HP + opex_fix_HP + elec_MWh * elec_price / 1e6) * 1e6
#                                        / annual_heat_MWh = LCOH_geo

target = geo_base["LCOH_EUR_per_MWh"]
hp = hp_base
fixed_costs_per_MWh = (hp["ann_capex_MEUR"] + hp["opex_fix_MEUR"]) * 1e6 \
                      / hp["annual_heat_MWh"]
elec_share_per_MWh_th_per_EUR = (hp["elec_MWh"] / hp["annual_heat_MWh"])
elec_breakeven = (target - fixed_costs_per_MWh) / elec_share_per_MWh_th_per_EUR

print("=== Break-even electricity price for HP=Geo LCOH ===")
print(f"  Target LCOH = {target:.2f} EUR/MWh (geothermal base case)")
print(f"  HP fixed-cost share = {fixed_costs_per_MWh:.2f} EUR/MWh_th")
print(f"  HP electricity demand per MWh_th = {elec_share_per_MWh_th_per_EUR:.3f} MWh_e/MWh_th")
print(f"  Break-even electricity price = {elec_breakeven:.2f} EUR/MWh_e")
print(f"  (this matches the project.tex thread 5 commentary that the breakeven price")
print(f"   is structurally negative, i.e. heat pumps cannot match geothermal LCOH")
print(f"   at any realistic positive electricity price under the base assumptions.)")


# %% [Verification against project.tex headline numbers]

EXPECTED_GEO_LCOH = 16.9         # from project.tex thread 5
EXPECTED_HP_LCOH = 66.8          # from project.tex thread 5

def assert_close(name: str, actual: float, expected: float, tol_pct: float = 1.0) -> None:
    diff_pct = abs(actual - expected) / expected * 100
    status = "OK" if diff_pct <= tol_pct else "MISMATCH"
    print(f"  [{status}] {name}: actual {actual:.2f}, "
          f"expected {expected:.2f}, diff {diff_pct:.2f}%")

print("=== Verification against project.tex ===")
assert_close("LCOH geothermal", geo_base["LCOH_EUR_per_MWh"], EXPECTED_GEO_LCOH)
assert_close("LCOH heat pump", hp_base["LCOH_EUR_per_MWh"], EXPECTED_HP_LCOH)
