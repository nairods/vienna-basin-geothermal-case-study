# Vienna Basin Geothermal — interactive case study tool

Single-file HTML companion to `project.tex`. Open `index.html` in any
modern browser; no server, no installation, no internet required (after
the first load — Plotly.js is fetched from CDN).

## What it does

Seven tabs, each driven by interactive sliders or filters:

1. **Overview** — Hero panel with the four headline numbers and a
   summary table of findings.
2. **LCOH calculator** — Sliders for geothermal CapEx / CF / OpEx and
   heat-pump CapEx / CF / COP / electricity price. The bar chart shows
   geothermal vs heat-pump LCOH and their carbon-credited versions at
   EU ETS 90 €/tCO₂ live as you move the sliders.
3. **Storage sizing** — The real Wien Energie LDC (Schubert 2022,
   2040 scenario, digitised) with a baseload overlay. Slide the
   doublet count, storage round-trip efficiency, and storage ΔT;
   feasibility, peak stored energy, and required storage volume
   recompute live.
4. **Seismicity map** — All 160 EMSC + USGS + GeoSphere events as a
   geographic scatter, colour-coded by DBSCAN cluster. Aspern (green
   star) and Ebreichsdorf (red triangle) markers; 15 km amber and
   30 km outer traffic-light radii. Magnitude filter slider.
5. **Thermal halo** — Single-doublet halo growth on log-log axes, with
   sliders for spacing L, aquifer thickness h, flow rate Q, porosity φ,
   and operating time t. Live read-out of thermal breakthrough time and
   spacing safety check.
6. **Hourly prices** — Mean Austrian wholesale electricity by hour of
   day and by month of year (2024–2025, Ember). Visualises the winter-
   evening peak that heat pumps cannot avoid.
7. **European benchmarks** — Bubble chart of Munich-Riem, Bavarian
   Molasse fleet, Paris Dogger, Reykjavík, Szeged, and the planned
   Aspern programme. Bubble size = households served; x = depth;
   y = reservoir temperature.

## Data sources baked in

| Element | Source | Status |
|---|---|---|
| 160 earthquake events | EMSC + USGS + GeoSphere, deduped, DBSCAN-clustered | reproducible via `scripts/geosphere_extract.py` + `scripts/seismicity_clusters.py` |
| Vienna LDC (30 points) | Schubert (2022) IEA Bioenergy Workshop p.8 | digitised by hand |
| Austrian hourly prices | Ember Energy, 99,788 points 2015–2026 | reproducible via `scripts/austria_price_stats.py` |
| Benchmark cases | Munich-Riem [52], Paris Dogger [30,31], Reykjavík [53], Szeged [54] | see project.tex references |

## How to use

Just open `index.html` in a browser. No build step. Designed for the
retreat — bring it up on a laptop, project it, and walk through
the findings by moving sliders.

Hosted offline-friendly: once the page has loaded once (which fetches
Plotly from `cdn.plot.ly`), it works without any network.

## Limitations

- Plotly.js is loaded from CDN. For a true offline-first build, download
  `plotly-2.35.2.min.js` and change the `<script src=...>` line to
  point at a local copy.
- The tool deliberately has *minimal text* — see `project.tex` for the
  full reasoning, citations, and audit trail.
