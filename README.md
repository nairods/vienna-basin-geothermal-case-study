# Vienna Basin geothermal case study --- reproducibility repository

This directory accompanies `project.tex` and lets a reader verify every
quantitative claim in it by running short Python scripts. Stdlib only;
no third-party packages are required for the analytical models.

## Layout

```
.
├── data/                              # Generated datasets (created on demand)
│   ├── austria_wholesale_hourly.csv  # Austrian hourly wholesale electricity prices (Ember)
│   ├── vienna_basin_catalog.csv      # Merged seismicity catalog (EMSC + USGS + GeoSphere)
│   ├── vienna_basin_catalog.geojson  # GeoJSON version of seismicity catalog
│   ├── vienna_basin_catalog_clustered.csv
│   │                                  # Cluster-labelled earthquake catalog (DBSCAN)
│   ├── vienna_basin_seed_events.csv  # Aspern-proximal seismic seed events
│   ├── vienna_basin_seed_events.geojson
│   ├── vienna_basin_seismicity.txt   # Gutenberg–Richter + catalog statistics
│   └── vienna_basin_xy.npz           # Cached projected seismic coordinates
│
├── figures/                           # Reproducible manuscript figures
│   ├── fig_halo.pdf                  # Thermal halo / interference figure
│   ├── fig_lcoh.pdf                  # Geothermal vs heat-pump LCOH comparison
│   ├── fig_ldc.pdf                   # Vienna district-heating load-duration curve
│   └── fig_seismicity.pdf            # Vienna Basin seismicity map
│
├── notebooks/                         # Core reproducibility scripts
│   ├── figures.py                    # Generate publication figures
│   ├── h2_montecarlo_dryell.py       # Dry-well drilling-risk Monte Carlo analysis
│   ├── m7_subsidence.py              # Surface subsidence estimate
│   ├── t4_storage.py                 # T4: seasonal storage vs doublet-count balance
│   ├── t4_storage_ldc.py             # T4: storage sizing using Vienna load-duration curve
│   ├── t5_lcoh.py                    # T5: levelised cost of heat (LCOH)
│   ├── t7_breakthrough.py            # T7: analytical thermal breakthrough estimate
│   └── t7_multidoublet.py            # T7: multi-doublet thermal interference
│
├── scripts/                           # Data acquisition & preprocessing
│   ├── austria_price_stats.py        # Austrian wholesale electricity price analysis
│   ├── geosphere_extract.py          # Vienna Basin seismic catalog extraction
│   └── seismicity_clusters.py        # DBSCAN clustering of seismic events
│
├── tool/                              # Interactive companion tool
│   ├── README.md                     # Tool-specific documentation
│   └── index.html                    # Offline interactive case-study dashboard
│
├── README.md                          # Repository overview and reproducibility guide
├── project.tex                        # Main case-study manuscript (primary artefact)
├── requirements.txt                   # Optional dependencies (figures, geospatial tools)
└── tool_data.json                     # Embedded interactive-tool dataset
```

## What this repository does and does not do

**Does:**
- reproduce every headline number in the analytical threads (T1, T4, T5, T7);
- produce CSV/GeoJSON exports for the T2 seed-events catalog;
- document the access routes for the four flagged external data items.

**Does not:**
- close the OMV Li/B/Cs chemistry gap (T3) --- that data does not exist
  publicly and the script honestly returns nothing;
- run reservoir simulation (T4/T7 are analytical only);
- fetch live data from any paywalled or non-public source.

## Cross-validation results

When the scripts were first run against the `project.tex` draft, the
verification blocks caught several numerical and labelling inconsistencies
in the manuscript (T5 sensitivity values, T4 storage volumes at non-base
parameters, T7 porosity-row ordering). These have been corrected in
`project.tex` as a result. This is exactly the value of the
reproducibility loop.

## Python version

Tested on Python 3.14. Should work on 3.10+.
