"""
M12 (Phase 3g): hourly Austrian wholesale electricity price stats.

Source: Ember Energy hourly European wholesale prices, Austria subset.
Used to refine the T5 LCOH heat-pump electricity-input assumption from
a single-point ~90 EUR/MWh to a weighted distribution over the
hours where a heat pump actually consumes electricity.

The fundamental question: does the HP "see" the annual-average price,
or does it see something higher (winter-weighted, evening-weighted)?

Stdlib only.
"""

import csv
import statistics
from collections import defaultdict
from pathlib import Path


PATH = Path(__file__).parent.parent / "data" / "austria_wholesale_hourly.csv"


# %% [Load]

rows = []
with open(PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        try:
            year = int(r["Datetime (UTC)"][:4])
            month = int(r["Datetime (UTC)"][5:7])
            hour_local = int(r["Datetime (Local)"][11:13])
            price = float(r["Price (EUR/MWhe)"])
            rows.append((year, month, hour_local, price))
        except (ValueError, KeyError):
            continue
print(f"loaded {len(rows)} hourly price points "
      f"({rows[0][0]}-{rows[-1][0]})")
print()


# %% [Stats]

def stats(prices):
    if not prices:
        return None
    return {
        "n": len(prices),
        "mean": statistics.mean(prices),
        "median": statistics.median(prices),
        "p10": statistics.quantiles(prices, n=10)[0],
        "p90": statistics.quantiles(prices, n=10)[8],
    }


# %% [Annual averages]

print("=== Annual mean wholesale price [EUR/MWh] ===")
for yr in sorted(set(r[0] for r in rows)):
    pr = [r[3] for r in rows if r[0] == yr]
    s = stats(pr)
    print(f"  {yr}: mean {s['mean']:7.2f}  median {s['median']:7.2f}  "
          f"p10 {s['p10']:7.2f}  p90 {s['p90']:7.2f}  n={s['n']}")
print()


# %% [Seasonal breakdown for 2024-2025]

print("=== Seasonal (winter Q1+Q4 vs summer Q2+Q3), 2024-2025 ===")
for yr in (2024, 2025):
    winter = [r[3] for r in rows if r[0] == yr and r[1] in (1, 2, 3, 10, 11, 12)]
    summer = [r[3] for r in rows if r[0] == yr and r[1] in (4, 5, 6, 7, 8, 9)]
    if not winter or not summer:
        continue
    print(f"  {yr} winter (Q1+Q4): mean {statistics.mean(winter):.2f}  "
          f"median {statistics.median(winter):.2f}  n={len(winter)}")
    print(f"  {yr} summer (Q2+Q3): mean {statistics.mean(summer):.2f}  "
          f"median {statistics.median(summer):.2f}  n={len(summer)}")
print()


# %% [Hour-of-day breakdown for 2024-2025]

print("=== Mean price by local hour-of-day (2024-2025 combined) ===")
by_hour = defaultdict(list)
for yr, _, h, p in rows:
    if yr in (2024, 2025):
        by_hour[h].append(p)
print(f"  hour  mean    median")
for h in range(24):
    if by_hour[h]:
        m = statistics.mean(by_hour[h])
        med = statistics.median(by_hour[h])
        bar = "#" * int(m / 5)
        print(f"  {h:02d}    {m:6.2f}  {med:6.2f}  {bar}")
print()


# %% [HP-relevant weighted price]

# A heat pump that follows winter heat demand consumes electricity:
#   - ~70% in winter half-year (Q1+Q4),
#   - ~30% in summer half-year (Q2+Q3),
#   - heavily concentrated in the evening peak (17-22 local) when DHW
#     and space-heating coincide.

# Build a simple HP demand weighting:
#   weight(month, hour) = (winter_factor) * (evening_factor)
# where winter_factor = 1.5 in Q1+Q4, 0.5 in Q2+Q3,
# evening_factor = 1.5 for hours 17-22, 1.0 for 6-17, 0.7 for 22-6.

def hp_weight(month, hour):
    w_season = 1.5 if month in (1, 2, 3, 10, 11, 12) else 0.5
    if 17 <= hour <= 22:
        w_hour = 1.5
    elif 6 <= hour <= 17:
        w_hour = 1.0
    else:
        w_hour = 0.7
    return w_season * w_hour


def weighted_mean(rows, weight_fn):
    total_w = 0.0
    total_wp = 0.0
    for yr, m, h, p in rows:
        w = weight_fn(m, h)
        total_w += w
        total_wp += w * p
    return total_wp / total_w if total_w > 0 else None


print("=== HP-weighted vs unweighted electricity price ===")
for yr in (2023, 2024, 2025):
    yr_rows = [r for r in rows if r[0] == yr]
    if not yr_rows:
        continue
    unw = statistics.mean(r[3] for r in yr_rows)
    weighted = weighted_mean(yr_rows, hp_weight)
    ratio = weighted / unw if unw else None
    print(f"  {yr}: unweighted {unw:6.2f}  HP-weighted {weighted:6.2f}  "
          f"ratio {ratio:.3f}")
print()


# %% [Recompute T5 LCOH-HP using the HP-weighted price]

# From T5 base case (notebooks/t5_lcoh.py):
HP_CAPEX_PER_MW = 1.3       # M EUR/MW_th
HP_OPEX_PCT = 0.05
HP_LIFETIME = 20
HP_CF = 0.50
HP_COP = 3.2
HP_P_MW = 55.0
r_disc = 0.05

# CRF
crf = r_disc * (1 + r_disc)**HP_LIFETIME / ((1 + r_disc)**HP_LIFETIME - 1)
capex = HP_CAPEX_PER_MW * HP_P_MW
ann_capex = capex * crf
opex_fix = HP_OPEX_PCT * capex
annual_heat = HP_P_MW * 8760 * HP_CF
elec_MWh = annual_heat / HP_COP

print("=== T5 HP LCOH refined with HP-weighted 2025 prices ===")
y_2025 = [r for r in rows if r[0] == 2025]
unw_2025 = statistics.mean(r[3] for r in y_2025)
hp_2025 = weighted_mean(y_2025, hp_weight)
y_2024 = [r for r in rows if r[0] == 2024]
unw_2024 = statistics.mean(r[3] for r in y_2024)
hp_2024 = weighted_mean(y_2024, hp_weight)

scenarios = [
    ("T5 frozen 90 EUR/MWh (base)",  90.0),
    ("2024 unweighted",              unw_2024),
    ("2024 HP-weighted",             hp_2024),
    ("2025 unweighted",              unw_2025),
    ("2025 HP-weighted",             hp_2025),
]
print(f"  {'scenario':<35} {'elec [EUR/MWh]':>14}  {'HP LCOH':>10}")
for desc, p in scenarios:
    opex_elec = elec_MWh * p / 1e6
    lcoh = (ann_capex + opex_fix + opex_elec) * 1e6 / annual_heat
    print(f"  {desc:<35} {p:>14.2f}  {lcoh:>10.2f}")
print()
print(f"Note: the geothermal LCOH base case (17 EUR/MWh) is unaffected;")
print(f"the comparison ratio shifts as the HP electricity cost shifts.")
