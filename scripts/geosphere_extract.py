"""
Vienna Basin earthquake-catalog extraction --- real pipeline.

Combines three open public sources to assemble a defensible baseline
seismicity catalog for the Vienna Basin (bounding box around the AFS,
Aspern site, and the southern-Vienna-Basin VBTF splay faults):

  1. EMSC SeismicPortal FDSN (https://www.seismicportal.eu/fdsnws/event/1/)
     -- European composite catalog ingesting national networks
     (ZAMG/GeoSphere Austria, BUD/Hungary, INGV/Italy, etc.).
     Resolution: ~M>=1.5 from ~1990 onwards.
  2. USGS FDSN  (https://earthquake.usgs.gov/fdsnws/event/1/)
     -- Global authoritative catalog, M>=2.5 in Europe, used as
     cross-check.
  3. GeoSphere Austria current-events JSON
     (https://www.geosphere.at/data/earthquakes)
     -- Rolling 14-day window with very fine resolution (M down to ~-1),
     useful for short-term baseline rates and recent-events snapshot.

Outputs (in data/):
  - vienna_basin_catalog.csv     : merged catalog
  - vienna_basin_catalog.geojson : same, GeoJSON FeatureCollection
  - vienna_basin_seismicity.txt  : statistics (b-value, rate, etc.)

Stdlib only. Network required. Run as `python3 scripts/geosphere_extract.py`.
"""

from __future__ import annotations

import csv
import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# Vienna Basin bounding box (Aspern + Aderklaa + Ebreichsdorf + AFS + VBTF splays):
LAT_MIN, LAT_MAX = 47.7, 48.5
LON_MIN, LON_MAX = 16.0, 17.0
MAG_MIN_LONGTERM = 1.5            # EMSC long-term cutoff
MAG_MIN_USGS = 2.5                # USGS cross-check cutoff
STARTTIME = "1990-01-01"
ENDTIME = "2026-05-20"

# Aspern site (for radius / distance metrics, approximate)
ASPERN_LAT, ASPERN_LON = 48.22, 16.50

USER_AGENT = "VB-geothermal-case-study/0.1 (academic; project.tex)"
TIMEOUT_S = 30


# %% [Data model]

@dataclass
class Event:
    source: str
    event_id: str
    datetime_utc: str
    latitude: float
    longitude: float
    depth_km: float | None
    magnitude: float
    magnitude_type: str | None
    region: str | None = None
    is_verified: bool | None = None


# %% [Distance utility (haversine in km)]

def hav_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


# %% [Sources]

def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read()


def fetch_emsc() -> list[Event]:
    """EMSC SeismicPortal FDSN, text format."""
    url = (f"https://www.seismicportal.eu/fdsnws/event/1/query?"
           f"format=text&starttime={STARTTIME}&endtime={ENDTIME}"
           f"&minlatitude={LAT_MIN}&maxlatitude={LAT_MAX}"
           f"&minlongitude={LON_MIN}&maxlongitude={LON_MAX}"
           f"&minmagnitude={MAG_MIN_LONGTERM}")
    print(f"  [EMSC] GET {url}")
    try:
        data = fetch_url(url).decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  [EMSC] HTTP {e.code}: {e}")
        return []
    events: list[Event] = []
    for line in data.splitlines():
        if not line or line.startswith("#"):
            continue
        # pipe-delimited:  EventID|Time|Lat|Lon|Depth|Author|Catalog|Contrib|ContribID|MagType|Mag|MagAuthor|Region
        f = line.split("|")
        if len(f) < 13:
            continue
        try:
            events.append(Event(
                source="EMSC",
                event_id=f[0],
                datetime_utc=f[1],
                latitude=float(f[2]),
                longitude=float(f[3]),
                depth_km=float(f[4]) if f[4] else None,
                magnitude=float(f[10]),
                magnitude_type=f[9],
                region=f[12],
            ))
        except (ValueError, IndexError):
            continue
    return events


def fetch_usgs() -> list[Event]:
    """USGS FDSN, GeoJSON format."""
    url = (f"https://earthquake.usgs.gov/fdsnws/event/1/query?"
           f"format=geojson&starttime={STARTTIME}&endtime={ENDTIME}"
           f"&minlatitude={LAT_MIN}&maxlatitude={LAT_MAX}"
           f"&minlongitude={LON_MIN}&maxlongitude={LON_MAX}"
           f"&minmagnitude={MAG_MIN_USGS}")
    print(f"  [USGS] GET {url}")
    try:
        data = json.loads(fetch_url(url))
    except urllib.error.HTTPError as e:
        print(f"  [USGS] HTTP {e.code}: {e}")
        return []
    events = []
    for feat in data.get("features", []):
        p = feat["properties"]
        c = feat["geometry"]["coordinates"]
        # USGS time is ms since epoch
        ts_ms = p.get("time")
        dt = datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).isoformat() if ts_ms else ""
        events.append(Event(
            source="USGS",
            event_id=feat.get("id", ""),
            datetime_utc=dt,
            latitude=c[1],
            longitude=c[0],
            depth_km=c[2] if len(c) > 2 else None,
            magnitude=p.get("mag", 0.0),
            magnitude_type=p.get("magType", ""),
            region=p.get("place", ""),
        ))
    return events


def fetch_geosphere() -> list[Event]:
    """GeoSphere Austria last-14-days catalog (very fine M resolution)."""
    url = "https://www.geosphere.at/data/earthquakes"
    print(f"  [GeoSphere] GET {url}")
    try:
        data = json.loads(fetch_url(url))
    except urllib.error.HTTPError as e:
        print(f"  [GeoSphere] HTTP {e.code}: {e}")
        return []
    events = []
    for e in data:
        if not (LAT_MIN <= e["lat"] <= LAT_MAX
                and LON_MIN <= e["lon"] <= LON_MAX):
            continue
        ref_mag = e.get("reference_magnitude") or [None, None]
        try:
            events.append(Event(
                source="GeoSphere",
                event_id=str(e.get("event_id", "")),
                datetime_utc=e.get("datetime_utc", ""),
                latitude=e["lat"],
                longitude=e["lon"],
                depth_km=e.get("depth"),
                magnitude=float(ref_mag[0]) if ref_mag[0] is not None else 0.0,
                magnitude_type=str(ref_mag[1]) if ref_mag[1] is not None else None,
                region=e.get("epicenter") or e.get("region"),
                is_verified=e.get("is_verified"),
            ))
        except (TypeError, ValueError):
            continue
    return events


# %% [Dedupe + filter]

def _parse_dt(s: str) -> datetime | None:
    """Parse a UTC datetime string into a tz-aware datetime, or None."""
    if not s:
        return None
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t


def dedupe(events: list[Event], time_tol_s: float = 60.0,
           dist_tol_km: float = 10.0) -> list[Event]:
    """Drop duplicates across sources by time+location proximity. Prefer
    GeoSphere > EMSC > USGS ordering for the keeper (most local first)."""
    order = {"GeoSphere": 0, "EMSC": 1, "USGS": 2}
    sorted_events = sorted(events, key=lambda e: (e.datetime_utc, order.get(e.source, 9)))
    out: list[Event] = []
    for e in sorted_events:
        t = _parse_dt(e.datetime_utc)
        if t is None:
            out.append(e); continue
        dup = False
        for prev in out[-50:]:
            t_prev = _parse_dt(prev.datetime_utc)
            if t_prev is None:
                continue
            if abs((t - t_prev).total_seconds()) > time_tol_s:
                continue
            if hav_km(e.latitude, e.longitude,
                     prev.latitude, prev.longitude) < dist_tol_km:
                dup = True
                break
        if not dup:
            out.append(e)
    return out


def in_vienna_basin(e: Event) -> bool:
    return (LAT_MIN <= e.latitude <= LAT_MAX
            and LON_MIN <= e.longitude <= LON_MAX)


# %% [Statistics]

def gutenberg_richter(events: list[Event], mag_bin: float = 0.25,
                       m_c: float = 2.5, m_upper: float = 4.5
                       ) -> tuple[list[tuple[float, float]], float | None, float | None]:
    """Return (cumulative distribution points, a, b) via least-squares
    on the linear segment between m_c (completeness magnitude) and
    m_upper (above which finite-catalog noise dominates).

    Default m_c = 2.5 reflects EMSC catalog completeness in this region;
    EMSC is known to be incomplete below ~M2 for the Vienna Basin since
    the regional networks (BUD, ZAMG/GeoSphere) report selectively.
    """
    mags = sorted(e.magnitude for e in events)
    if not mags:
        return [], None, None
    m_lo = math.floor(min(mags) / mag_bin) * mag_bin
    m_hi = math.ceil(max(mags) / mag_bin) * mag_bin
    points = []
    M = m_lo
    while M <= m_hi + 1e-9:
        n = sum(1 for x in mags if x >= M - 1e-9)
        if n > 0:
            points.append((round(M, 2), math.log10(n)))
        M += mag_bin

    # Fit on [m_c, m_upper]
    xs = [p[0] for p in points if m_c - 1e-9 <= p[0] <= m_upper + 1e-9]
    ys = [p[1] for p in points if m_c - 1e-9 <= p[0] <= m_upper + 1e-9]
    if len(xs) < 3:
        return points, None, None
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return points, None, None
    slope = num / den
    intercept = mean_y - slope * mean_x
    return points, intercept, -slope  # b = -slope


def annual_rate(events: list[Event], m_min: float) -> float:
    """Events per year above magnitude m_min."""
    filtered = [e for e in events if e.magnitude >= m_min]
    if not filtered:
        return 0.0
    times = [t for t in (_parse_dt(e.datetime_utc) for e in filtered) if t]
    if len(times) < 2:
        return 0.0
    span_yr = (max(times) - min(times)).total_seconds() / (365.25 * 86400)
    if span_yr <= 0:
        return 0.0
    return len(filtered) / span_yr


# %% [Distance metrics from Aspern]

def near_aspern(events: list[Event], radius_km: float = 15.0) -> list[Event]:
    return [e for e in events
            if hav_km(e.latitude, e.longitude, ASPERN_LAT, ASPERN_LON) <= radius_km]


# %% [Export]

def export_csv(events: list[Event], path: Path) -> None:
    fields = ["source", "event_id", "datetime_utc", "latitude", "longitude",
              "depth_km", "magnitude", "magnitude_type", "region", "is_verified"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in events:
            w.writerow(asdict(e))


def export_geojson(events: list[Event], path: Path) -> None:
    feats = []
    for e in events:
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [e.longitude, e.latitude,
                                         e.depth_km or 0]},
            "properties": {k: v for k, v in asdict(e).items()
                           if k not in ("latitude", "longitude")},
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, indent=2)


# %% [Main]

def main() -> None:
    out = Path(__file__).parent.parent / "data"
    out.mkdir(exist_ok=True)

    print("=== Vienna Basin earthquake-catalog extraction ===")
    print(f"  bbox: [{LAT_MIN}..{LAT_MAX}]N, [{LON_MIN}..{LON_MAX}]E")
    print(f"  time: {STARTTIME} to {ENDTIME}")
    print(f"  M cutoffs: EMSC {MAG_MIN_LONGTERM}, USGS {MAG_MIN_USGS}")
    print()

    emsc = fetch_emsc()
    print(f"  EMSC raw events: {len(emsc)}")
    usgs = fetch_usgs()
    print(f"  USGS raw events: {len(usgs)}")
    gsa = fetch_geosphere()
    print(f"  GeoSphere (14d) Vienna Basin events: {len(gsa)}")
    print()

    merged = emsc + usgs + gsa
    merged_filtered = [e for e in merged if in_vienna_basin(e)]
    deduped = dedupe(merged_filtered)
    print(f"  Merged Vienna Basin events: {len(merged_filtered)}")
    print(f"  After dedup (60s, 10km): {len(deduped)}")
    print()

    # Sort chronologically for export
    deduped.sort(key=lambda e: e.datetime_utc)

    csv_path = out / "vienna_basin_catalog.csv"
    gj_path = out / "vienna_basin_catalog.geojson"
    export_csv(deduped, csv_path)
    export_geojson(deduped, gj_path)
    print(f"  wrote {csv_path}")
    print(f"  wrote {gj_path}")
    print()

    # --- Statistics ---
    print("=== Statistics for the Vienna Basin baseline ===")

    points, a, b = gutenberg_richter(deduped)
    print(f"  Gutenberg-Richter log10 N(>=M) = a - b*M")
    if a is not None and b is not None:
        print(f"    a = {a:.2f}, b = {b:.2f}")
        print(f"  (typical natural-tectonic b values are 0.7--1.1;")
        print(f"   anomalously high b is a flag for ongoing fluid-driven swarms.)")
    print(f"  Cumulative distribution points (M, log10 N):")
    for M, logN in points:
        print(f"    M >= {M:4.2f}: log10 N = {logN:.2f}   (N = {10**logN:.0f})")
    print()

    print(f"  Annual rate (events/yr) in bbox:")
    for m_cut in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
        rate = annual_rate(deduped, m_cut)
        print(f"    M >= {m_cut}: {rate:.2f} /yr")
    print()

    aspern_15 = near_aspern(deduped, 15.0)
    aspern_30 = near_aspern(deduped, 30.0)
    print(f"  Near Aspern site ({ASPERN_LAT}N, {ASPERN_LON}E):")
    print(f"    within 15 km: {len(aspern_15)} events  ({sum(1 for e in aspern_15 if e.magnitude >= 2):d} of these M>=2)")
    print(f"    within 30 km: {len(aspern_30)} events  ({sum(1 for e in aspern_30 if e.magnitude >= 2):d} of these M>=2)")
    print()

    largest = sorted(deduped, key=lambda e: -e.magnitude)[:10]
    print(f"  Top 10 largest events in Vienna Basin bbox (1990-2026):")
    for e in largest:
        d = hav_km(e.latitude, e.longitude, ASPERN_LAT, ASPERN_LON)
        print(f"    {e.datetime_utc[:10]}  M{e.magnitude:>4.1f}  {e.region}  [{e.source}, "
              f"{d:.1f} km from Aspern]")
    print()

    # --- Write summary ---
    summary_path = out / "vienna_basin_seismicity.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Vienna Basin baseline seismicity (T2 input).\n")
        f.write(f"bbox: [{LAT_MIN}..{LAT_MAX}]N, [{LON_MIN}..{LON_MAX}]E\n")
        f.write(f"time: {STARTTIME} to {ENDTIME}\n")
        f.write(f"total events (M>={MAG_MIN_LONGTERM}, deduped): {len(deduped)}\n\n")
        if a is not None and b is not None:
            f.write(f"Gutenberg-Richter: log10 N(>=M) = {a:.2f} - {b:.2f}*M\n")
            f.write(f"  (natural-tectonic b range: 0.7--1.1; \n"
                    f"   b > ~1.2 may indicate fluid-driven swarms)\n\n")
        f.write("Annual rates (events/yr in bbox):\n")
        for m_cut in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
            f.write(f"  M >= {m_cut}: {annual_rate(deduped, m_cut):.2f}\n")
        f.write("\n")
        f.write(f"Events within 15 km of Aspern: {len(aspern_15)}\n")
        f.write(f"Events within 30 km of Aspern: {len(aspern_30)}\n")
        f.write("\nTop 10 largest events:\n")
        for e in largest:
            d = hav_km(e.latitude, e.longitude, ASPERN_LAT, ASPERN_LON)
            f.write(f"  {e.datetime_utc[:10]}  M{e.magnitude:.1f}  {e.region} "
                    f"({e.source}, {d:.1f} km from Aspern)\n")
    print(f"  wrote {summary_path}")


if __name__ == "__main__":
    main()
