"""
GeoSphere Austria earthquake-catalog extraction --- documented routes.

This script is a SKELETON, not a working pipeline. As of 2026-05-20 the
GeoSphere Data Hub API at https://dataset.api.hub.geosphere.at/v1/
exposes only weather/climate/station datasets; the Austrian Earthquake
Catalogue (AEC) is NOT a public dataset endpoint. The three known routes
to access AEC data are documented in `GeoSphere.md` and reproduced here.

What this script does today:
  - verifies the Data Hub API is up and lists its datasets;
  - implements the data-shape we WILL want once an AEC endpoint exists
    or has been received from seismo@geosphere.at;
  - includes a bounding-box filter and a tiny Gutenberg-Richter
    placeholder for the Vienna Basin subset.

What this script does NOT do today:
  - it does not return any actual earthquake events. There is no public
    JSON endpoint.

To extend this into a working pipeline, the maintainer should either
(a) email seismo@geosphere.at with the bounding box below for a custom
catalog export, or (b) digitise the public earthquake list at
https://www.geosphere.at/en/maps/current-earthquakes (a React-rendered
page; requires headless-browser scraping).

Stdlib only. Run as `python3 scripts/geosphere_extract.py`.
"""

from __future__ import annotations

import csv
import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

DATA_HUB_API = "https://dataset.api.hub.geosphere.at/v1"
TIMEOUT_S = 10

# Vienna Basin bounding box (approximate; covers Aspern, Aderklaa, AFS area,
# Ebreichsdorf, southern Vienna Basin):
LAT_MIN, LAT_MAX = 47.7, 48.5
LON_MIN, LON_MAX = 16.0, 17.0
MAG_MIN = 0.5            # cutoff for completeness


# %% [Data model]

@dataclass
class Event:
    event_id: str
    datetime_utc: str       # ISO 8601
    latitude: float
    longitude: float
    depth_km: float | None
    magnitude: float
    magnitude_type: str | None
    region: str | None
    source: str
    felt_intensity: str | None = None   # EMS-98 if reported
    induced_classification: str | None = None


def in_vienna_basin(ev: Event) -> bool:
    return (LAT_MIN <= ev.latitude <= LAT_MAX
            and LON_MIN <= ev.longitude <= LON_MAX)


# %% [Route 1 --- probe the Data Hub for any earthquake-tagged dataset]

def probe_data_hub() -> list[dict]:
    """Return all datasets from the Data Hub, filtered to anything that
    might be earthquake-related."""
    url = f"{DATA_HUB_API}/datasets"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  [WARN] data hub unreachable: {e}")
        return []
    quake_like = [d for d in data
                  if isinstance(d, dict) and any(
                      kw in (d.get("title", "") + " " + d.get("id", "")).lower()
                      for kw in ("earthquake", "erdbeben", "seismic",
                                 "seismo", "aec", "quake")
                  )]
    return quake_like


def list_all_datasets() -> list[str]:
    """List dataset IDs from the Data Hub (for documentation/verification)."""
    url = f"{DATA_HUB_API}/datasets"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError) as e:
        return []
    ids = []
    if isinstance(data, dict):
        # may be a nested mapping
        for k, v in data.items():
            if isinstance(v, dict) and v.get("type") == "Dataset":
                ids.append(k)
            elif isinstance(v, list):
                for entry in v:
                    if isinstance(entry, dict) and "id" in entry:
                        ids.append(entry["id"])
    elif isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                ids.append(entry.get("id", "?"))
    return ids


# %% [Route 2 --- structured stub event ready to be filled in]

# When AEC data are obtained (from email request or scraping), populate this
# list and the rest of the pipeline runs on it.
SEED_EVENTS: list[Event] = [
    # Verified events from the F5 baseline statistics in project.tex.
    # Magnitudes from cited sources (refs [6, 7, 8]).
    Event(
        event_id="EBR2000",
        datetime_utc="2000-07-11T00:00:00Z",
        latitude=47.95,
        longitude=16.40,
        depth_km=None,
        magnitude=4.8,
        magnitude_type="ML",
        region="Ebreichsdorf",
        source="GeoSphere Austria (formerly ZAMG) catalog; project.tex F5"
    ),
    Event(
        event_id="EBR2013A",
        datetime_utc="2013-09-20T00:00:00Z",
        latitude=47.95,
        longitude=16.40,
        depth_km=None,
        magnitude=4.3,
        magnitude_type="ML",
        region="Ebreichsdorf",
        source="GeoSphere Austria; project.tex F5"
    ),
    Event(
        event_id="EBR2024",
        datetime_utc="2024-04-14T00:00:00Z",
        latitude=47.95,
        longitude=16.40,
        depth_km=None,
        magnitude=3.0,
        magnitude_type="ML",
        region="Ebreichsdorf (VBTF normal splay)",
        source="GeoSphere Austria; project.tex F5"
    ),
    Event(
        event_id="CARNUNTUM_4C",
        datetime_utc="0350-01-01T00:00:00Z",
        latitude=48.10,
        longitude=16.85,
        depth_km=None,
        magnitude=6.5,
        magnitude_type="Mw_est",
        region="Carnuntum (Roman archaeological evidence)",
        source="Hintersberger & Decker 2018 [6]"
    ),
]


# %% [Filter and basic stats]

def vienna_basin_subset(events: Iterable[Event]) -> list[Event]:
    return [e for e in events if in_vienna_basin(e) and e.magnitude >= MAG_MIN]


def gutenberg_richter_log_n(events: Iterable[Event], mag_bin: float = 0.5):
    """Return list of (M_cutoff, log10(N>=M))."""
    mags = sorted(e.magnitude for e in events)
    if not mags:
        return []
    m_lo = math.floor(min(mags) * 2) / 2
    m_hi = math.ceil(max(mags) * 2) / 2
    results = []
    M = m_lo
    while M <= m_hi:
        n = sum(1 for x in mags if x >= M)
        if n > 0:
            results.append((M, math.log10(n)))
        M += mag_bin
    return results


def export_csv(events: list[Event], path: Path) -> None:
    fields = list(asdict(events[0]).keys()) if events else \
             [f.name for f in Event.__dataclass_fields__.values()]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for e in events:
            writer.writerow(asdict(e))


def export_geojson(events: list[Event], path: Path) -> None:
    feats = []
    for e in events:
        feats.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [e.longitude, e.latitude]
            },
            "properties": {
                k: v for k, v in asdict(e).items()
                if k not in ("latitude", "longitude")
            }
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, indent=2)


# %% [Main]

def main() -> None:
    out = Path(__file__).parent.parent / "data"
    out.mkdir(exist_ok=True)

    print("=== Step 1: probe GeoSphere Data Hub for earthquake datasets ===")
    quake_datasets = probe_data_hub()
    if quake_datasets:
        for d in quake_datasets:
            print(f"  found: {d.get('id', '?')}  --  {d.get('title', '')}")
    else:
        print("  no earthquake dataset endpoint advertised; using seed data only.")

    print()
    print("=== Step 2: filter Vienna Basin subset ===")
    subset = vienna_basin_subset(SEED_EVENTS)
    for e in subset:
        print(f"  {e.datetime_utc[:10]}  M{e.magnitude:.1f}  "
              f"{e.region}  ({e.source})")
    print(f"  ({len(subset)} events in bbox [{LAT_MIN}..{LAT_MAX}]N, "
          f"[{LON_MIN}..{LON_MAX}]E, M >= {MAG_MIN})")

    print()
    print("=== Step 3: Gutenberg-Richter placeholder ===")
    gr = gutenberg_richter_log_n(subset)
    for M, logN in gr:
        print(f"  M >= {M:.1f}: log10(N) = {logN:.2f}")
    print("  (this is a placeholder on 4 seed events; full catalog needed")
    print("   for a real b-value estimate.)")

    print()
    print("=== Step 4: export ===")
    csv_path = out / "vienna_basin_seed_events.csv"
    gj_path = out / "vienna_basin_seed_events.geojson"
    export_csv(subset, csv_path)
    export_geojson(subset, gj_path)
    print(f"  wrote {csv_path}")
    print(f"  wrote {gj_path}")

    print()
    print("=== Next steps for whoever picks this up ===")
    print("  1. Email seismo@geosphere.at requesting the AEC subset for the")
    print("     bbox above with M >= 0.5, 1990-present, in CSV or GeoJSON.")
    print("  2. OR scrape the React-rendered list at")
    print("     https://www.geosphere.at/en/maps/current-earthquakes")
    print("     (requires headless browser; out of scope for stdlib).")
    print("  3. Drop the resulting CSV into data/ and rerun this script;")
    print("     the same downstream pipeline (filter, GR, export) will work.")


if __name__ == "__main__":
    main()
