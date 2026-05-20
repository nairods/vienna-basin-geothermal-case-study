"""
Generate the four headline figures for project.tex:
  fig_seismicity.pdf   --- Vienna Basin seismicity map with DBSCAN clusters
  fig_ldc.pdf          --- Wien Energie LDC, two-block model, and N-doublet
                           sizing curves
  fig_lcoh.pdf         --- LCOH for geothermal vs heat pump with sensitivity bars
  fig_halo.pdf         --- Single-doublet thermal halo radius vs time +
                           multi-doublet hex-grid sketch

Output: PDF files in figures/, sized for inclusion in the LaTeX document
via \includegraphics{figures/<name>}.

Requires numpy, matplotlib, scikit-learn. Run with the miniforge Python:
  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 notebooks/figures.py
"""

import math
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import DBSCAN


# Globally consistent style
plt.rcParams.update({
    "font.size": 9,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})


OUT = Path(__file__).parent.parent / "figures"
OUT.mkdir(exist_ok=True)


# %% [Fig 1: seismicity map with DBSCAN clusters]

def fig_seismicity():
    data = np.load(Path(__file__).parent.parent / "data" /
                   "vienna_basin_xy.npz")
    X = data["X"]
    mags = data["mags"]
    aspern_xy = data["aspern_xy"]
    ebr_xy = data["ebreichsdorf_xy"]

    # Re-run DBSCAN at the canonical setting
    labels = DBSCAN(eps=8.0, min_samples=5).fit_predict(X)

    fig, ax = plt.subplots(figsize=(6.5, 5.5))

    # Plot events: marker size scaled by magnitude, color by cluster
    cluster_colors = {
        -1: "lightgrey",         # noise
        0:  "#cc6677",           # southern VB / Ebreichsdorf
        1:  "#4477aa",           # Fischamend / NE Aspern
        2:  "#ddcc77",           # NE corner / Marchfeld
    }
    for lab in sorted(set(labels)):
        m = labels == lab
        color = cluster_colors.get(lab, "black")
        name = {
            -1: "noise / isolated",
            0: f"C0 southern VB / Ebreichsdorf (n={int(m.sum())})",
            1: f"C1 Fischamend / E of Aspern (n={int(m.sum())})",
            2: f"C2 Marchfeld (n={int(m.sum())})",
        }.get(lab, f"C{lab}")
        sizes = 8 + 22 * (mags[m] - 1.0)
        ax.scatter(X[m, 0], X[m, 1], s=sizes,
                   c=color, alpha=0.6, edgecolors="black",
                   linewidths=0.4, label=name)

    # Aspern + Ebreichsdorf markers
    ax.plot(*aspern_xy, marker="*", markersize=18, color="darkgreen",
            markeredgecolor="black", markeredgewidth=1.0,
            linestyle="none", zorder=10, label="Aspern (planned site)")
    ax.plot(*ebr_xy, marker="^", markersize=11, color="darkred",
            markeredgecolor="black", markeredgewidth=0.6,
            linestyle="none", zorder=10, label="Ebreichsdorf")

    # 15 km T2 traffic-light radius around Aspern
    circle = plt.Circle(aspern_xy, 15, fill=False, color="darkgreen",
                        linestyle="--", linewidth=1.2,
                        label="Aspern 15 km traffic-light zone")
    ax.add_patch(circle)
    # 30 km outer radius
    circle2 = plt.Circle(aspern_xy, 30, fill=False, color="darkgreen",
                         linestyle=":", linewidth=0.9,
                         label="30 km outer zone")
    ax.add_patch(circle2)

    # VBTF approximate trace (NE-SW through the basin)
    # Approximate by line from (47.7, 16.0) to (48.4, 17.0) in lat/lon,
    # projected.
    LAT_C = float(data["lat_c"])
    LON_C = float(data["lon_c"])
    deg_lat = float(data["deg_lat_km"])
    deg_lon = float(data["deg_lon_km"])
    def _proj(lat, lon):
        return ((lon - LON_C) * deg_lon, (lat - LAT_C) * deg_lat)
    x1, y1 = _proj(47.75, 16.05)
    x2, y2 = _proj(48.40, 16.95)
    ax.plot([x1, x2], [y1, y2], color="purple", lw=1.2, alpha=0.5,
            linestyle="-.", label="VBTF approx.")

    # Axes
    # Show ticks in km offset from centre (already in km)
    ax.set_aspect("equal")
    ax.set_xlabel("E-W [km from 16.5°E]")
    ax.set_ylabel("N-S [km from 48.1°N]")
    ax.set_title("Vienna Basin seismicity 1990--2026 (EMSC+USGS+GeoSphere, n=160)\n"
                 "DBSCAN clusters (eps=8 km, min_samples=5)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=7, framealpha=0.9)
    plt.tight_layout()
    plt.savefig(OUT / "fig_seismicity.pdf", bbox_inches="tight")
    plt.close()
    print(f"  wrote {OUT/'fig_seismicity.pdf'}")


# %% [Fig 2: LDC + two-block comparison + baseload sizing]

def fig_ldc():
    # Digitised LDC (same as t4_storage_ldc.py)
    ldc_samples = [
        (1, 47.5), (5, 43.0), (10, 40.0), (15, 37.5), (20, 35.5),
        (25, 33.5), (30, 31.5), (35, 30.0), (40, 28.5), (50, 25.5),
        (60, 23.5), (70, 21.5), (80, 19.5), (90, 18.0), (100, 17.0),
        (115, 15.5), (130, 14.0), (145, 12.8), (160, 11.5), (180, 10.0),
        (200, 8.8), (220, 7.7), (240, 6.8), (260, 6.0), (280, 5.4),
        (300, 5.0), (320, 4.5), (340, 3.8), (355, 3.2), (365, 2.8),
    ]
    days = np.arange(1, 366)
    rs = np.array([r for r, _ in ldc_samples])
    vs = np.array([v for _, v in ldc_samples])
    ldc = np.interp(days, rs, vs)  # GWh/day, sorted descending

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Left: LDC + two-block model overlay
    ax = axes[0]
    ax.fill_between(days, ldc, color="#aaccee", alpha=0.5,
                    label="Schubert (2022) LDC")
    ax.plot(days, ldc, color="navy", lw=1.5)

    # Two-block model: D_w=1000 MW for first half, D_s=370 MW for second
    P_DOUBLET_MW = 18.8
    CF = 0.85
    P_eff = P_DOUBLET_MW * CF
    D_w_GWhd = 1000 * 24 / 1000
    D_s_GWhd = 370 * 24 / 1000
    two_block = np.concatenate([
        np.full(int(365/2), D_w_GWhd),
        np.full(365 - int(365/2), D_s_GWhd),
    ])
    ax.plot(days, np.sort(two_block)[::-1], color="darkred", lw=1.2,
            linestyle="--", label="Two-block model")

    # Baselines: 39 doublets, 46 doublets
    for N, color, lbl in [(39, "green", "N=39 (LDC opt.)"),
                          (46, "orange", "N=46 (two-block)")]:
        baseload_GWhd = N * P_eff * 24 / 1000
        ax.axhline(baseload_GWhd, color=color, lw=1, linestyle=":",
                   label=f"{lbl}: {baseload_GWhd:.1f} GWh/d")

    ax.set_xlabel("Day rank (1 = peak)")
    ax.set_ylabel("Daily heat demand [GWh/d]")
    ax.set_title("Load duration curve (Schubert 2022, Vienna 2040 scenario)")
    ax.legend(loc="upper right", fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 365)
    ax.set_ylim(0, 55)

    # Right: doublet count vs storage volume
    ax = axes[1]
    ETA = 0.70
    DELTA_T = 60.0
    Ns = np.arange(10, 90)
    storage_vols = []
    feasibility = []
    for N in Ns:
        baseload_GWhd = N * P_eff * 24 / 1000
        cumulative = 0.0
        peak_stored = 0.0
        deficit = 0.0
        surplus = 0.0
        for d in ldc:
            delta = baseload_GWhd - d
            if delta >= 0:
                surplus += delta
                cumulative += delta * ETA
            else:
                deficit += -delta
                cumulative -= -delta
            peak_stored = max(peak_stored, cumulative)
        V = peak_stored * 1e9 * 3600 / (1000 * 4180 * DELTA_T)
        storage_vols.append(V / 1e6)  # million m^3
        feasibility.append(surplus * ETA >= deficit)

    storage_vols = np.array(storage_vols)
    feasibility = np.array(feasibility)
    ax.plot(Ns[feasibility], storage_vols[feasibility], "o-",
            color="navy", lw=1.5, markersize=4, label="Feasible (LDC-based)")
    ax.plot(Ns[~feasibility], np.zeros(int((~feasibility).sum())),
            "x", color="lightgrey", label="Energy-balance infeasible")
    # Two-block estimate for comparison
    ax.axhline(23.0, color="darkred", linestyle="--", lw=1,
               label="Two-block N=46: 23 M m³")
    ax.axvline(39, color="green", linestyle=":", lw=1)
    ax.axvline(46, color="orange", linestyle=":", lw=1)
    ax.set_xlabel("Doublet count $N$")
    ax.set_ylabel("Required storage volume [10$^6$ m³]")
    ax.set_title("Storage requirement vs N (eta=0.70, deltaT=60 K)")
    ax.legend(loc="upper left", fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_yscale("symlog", linthresh=0.5)
    ax.set_ylim(0, 80)

    plt.tight_layout()
    plt.savefig(OUT / "fig_ldc.pdf", bbox_inches="tight")
    plt.close()
    print(f"  wrote {OUT/'fig_ldc.pdf'}")


# %% [Fig 3: LCOH with sensitivity bars]

def fig_lcoh():
    # From notebooks/t5_lcoh.py
    geo_base = 16.93
    hp_base = 66.78
    sensitivities = [
        ("Base case",                geo_base, hp_base),
        ("Geo CapEx +50%",           25.40,   hp_base),
        ("Geo CF -> 0.70",           20.56,   hp_base),
        ("Geo OpEx -> 5%",           21.63,   hp_base),
        ("HP elec 180 EUR/MWh",      geo_base, 94.91),
        ("HP CF -> 0.30",            geo_base, 92.55),
        ("HP COP -> 2.5",            geo_base, 74.66),
        ("Worst-of-both",            39.40,   54.28),
    ]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    y_positions = np.arange(len(sensitivities))[::-1]
    width = 0.4
    geo_vals = [s[1] for s in sensitivities]
    hp_vals = [s[2] for s in sensitivities]
    labels = [s[0] for s in sensitivities]

    ax.barh(y_positions + width/2, geo_vals, height=width, color="#117733",
            alpha=0.8, label="Geothermal")
    ax.barh(y_positions - width/2, hp_vals, height=width, color="#cc6677",
            alpha=0.8, label="Heat pump")

    for i, (yp, g, h) in enumerate(zip(y_positions, geo_vals, hp_vals)):
        ax.text(g + 1, yp + width/2, f"{g:.1f}",
                va="center", fontsize=7)
        ax.text(h + 1, yp - width/2, f"{h:.1f}",
                va="center", fontsize=7)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.set_xlabel("LCOH [EUR/MWh$_{\\mathrm{th}}$]")
    ax.set_title("Levelised cost of heat: geothermal vs.\\ heat pump\n"
                 "(deep Vienna Basin doublet vs.\\ Ebswien wastewater HP)")
    ax.legend(loc="lower right")
    ax.grid(True, axis="x", alpha=0.3)
    ax.set_xlim(0, 110)
    plt.tight_layout()
    plt.savefig(OUT / "fig_lcoh.pdf", bbox_inches="tight")
    plt.close()
    print(f"  wrote {OUT/'fig_lcoh.pdf'}")


# %% [Fig 4: thermal halo + multi-doublet hex grid]

def fig_halo():
    # Halo growth (from t7_multidoublet.py)
    times_yr = np.array([1, 2, 5, 10, 20, 30, 50, 100])
    PHI = 0.20
    RHOC_W = 4.18e6
    RHOC_R = 2.20e6
    RHOC_B = PHI * RHOC_W + (1 - PHI) * RHOC_R
    H = 100.0
    Q = 0.075
    r_halo = np.sqrt(Q * times_yr * 365.25 * 86400 * RHOC_W / RHOC_B
                      / (np.pi * H))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # Left: r_halo vs t with interaction lines
    ax = axes[0]
    ax.plot(times_yr, r_halo, "o-", color="navy", lw=1.5,
            markersize=6, label="$r_{\\mathrm{halo}}(t)$")
    # Critical spacing for 30-yr: 1.21 km
    ax.axhline(1207, color="darkred", linestyle="--", lw=1,
               label="$D_{\\mathrm{crit}}=1.21$ km (at 30 yr)")
    # Hex-grid spacing at N=40 in 1500 km^2: 3.8 km
    ax.axhline(3800, color="darkgreen", linestyle=":", lw=1,
               label="Hex-grid spacing 3.8 km (N=40 in 1500 km²)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Time [yr]")
    ax.set_ylabel("Halo radius / spacing [m]")
    ax.set_title("Single-doublet thermal halo growth")
    ax.legend(loc="lower right", fontsize=7)
    ax.grid(True, which="both", alpha=0.3)

    # Right: hex-grid sketch with 30-yr halos
    ax = axes[1]
    # Place 40 doublets on a hex grid in 1500 km^2 = ~38.7 km square
    L = math.sqrt(1500)  # km
    spacing_km = 3.8
    # Hex grid: even rows offset by spacing_km/2
    points = []
    row = 0
    y = 0.0
    while y < L:
        x_offset = (spacing_km / 2) if (row % 2 == 1) else 0.0
        x = x_offset
        while x < L:
            points.append((x, y))
            x += spacing_km
        y += spacing_km * math.sqrt(3) / 2
        row += 1
    # Limit to 40
    if len(points) > 40:
        # Sort by distance from centre, take centermost 40
        cx, cy = L/2, L/2
        points.sort(key=lambda p: (p[0]-cx)**2 + (p[1]-cy)**2)
        points = points[:40]

    for p in points:
        # Plot 30-yr halo as filled circle (radius 0.6 km)
        ax.add_patch(plt.Circle(p, 0.603, color="lightblue",
                                alpha=0.6, ec="navy", lw=0.5))

    # Mark a "centre" doublet
    cx, cy = L/2, L/2
    nearest = min(points, key=lambda p: (p[0]-cx)**2 + (p[1]-cy)**2)
    ax.plot(nearest[0], nearest[1], marker="*", markersize=15,
            color="red", markeredgecolor="black",
            linestyle="none", label="Centre doublet")

    ax.set_xlim(0, L)
    ax.set_ylim(0, L)
    ax.set_aspect("equal")
    ax.set_xlabel("E-W [km]")
    ax.set_ylabel("N-S [km]")
    ax.set_title(f"N=40 doublets on 3.8 km hex grid (1500 km²) +\n"
                 f"30-yr thermal halos (r=603 m). Halos do not touch.")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=7)

    plt.tight_layout()
    plt.savefig(OUT / "fig_halo.pdf", bbox_inches="tight")
    plt.close()
    print(f"  wrote {OUT/'fig_halo.pdf'}")


# %% [Main]

if __name__ == "__main__":
    print("Generating figures...")
    fig_seismicity()
    fig_ldc()
    fig_lcoh()
    fig_halo()
    print("Done.")
