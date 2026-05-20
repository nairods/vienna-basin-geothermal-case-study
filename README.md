# Vienna Basin geothermal case study --- reproducibility repository

This directory accompanies `project.tex` and lets a reader verify every
quantitative claim in it by running short Python scripts. Stdlib only;
no third-party packages are required for the analytical models.

## Layout

```
project.tex                    -- the case-study document (this is the main artefact)
notebooks/
  t5_lcoh.py                   -- thread 5 levelised-cost-of-heat
  t4_storage.py                -- thread 4 doublet-vs-storage energy balance
  t7_breakthrough.py           -- thread 7 thermal-breakthrough estimate
scripts/
  geosphere_extract.py         -- GeoSphere Austria AEC extraction skeleton (T2)
data/                          -- created on demand by scripts
requirements.txt               -- optional packages (figures, geopandas)
dh-demand.md                   -- support file on Vienna DH demand reconstruction
Aderklaa-96.md                 -- support file on the OMV/Wien Energie test well
OMV.md                         -- support file on OMV produced-water chemistry
GeoSphere.md                   -- support file on AEC catalog access
```

## Reproducing the numbers in `project.tex`

```bash
python3 notebooks/t5_lcoh.py        # reproduces thread 5 LCOH table
python3 notebooks/t4_storage.py     # reproduces thread 4 doublet+storage table
python3 notebooks/t7_breakthrough.py # reproduces thread 7 breakthrough table
python3 scripts/geosphere_extract.py # documents the T2 catalog route + seed events
```

Each script ends with a verification block that asserts the script's
computed values match the headline numbers cited in `project.tex` within
2% tolerance. Any mismatch is reported with the `[MISMATCH]` tag.

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
