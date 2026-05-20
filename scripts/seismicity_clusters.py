"""
Vienna Basin seismicity clustering --- T2 traffic-light refinement.

Question: do AFS-proximal events (around Aspern, the planned Wien Energie
geothermal site) form a statistically distinct cluster from the
Ebreichsdorf / southern-Vienna-Basin cluster? Answering this refines the
10-km traffic-light monitoring radius proposed in T2.

Method:
  * load the 160-event Vienna Basin catalog produced by
    scripts/geosphere_extract.py;
  * run DBSCAN (density-based) with several (eps, min_samples) settings
    on equirectangular-projected coordinates (km);
  * run k-means with k=2,3,4 for comparison;
  * report cluster statistics including a quantitative test for
    "is Aspern in the same cluster as Ebreichsdorf?"

Dependencies: numpy, scikit-learn, pandas (optional --- we use stdlib csv).
"""

import csv
import math
from pathlib import Path

import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score


# %% [Site reference points]

ASPERN_LAT, ASPERN_LON = 48.22, 16.50              # T2/F5 frozen
EBREICHSDORF_LAT, EBREICHSDORF_LON = 47.95, 16.40  # Ebreichsdorf cluster centre

# Equirectangular projection origin (centre of bbox)
LAT_C = 48.10
LON_C = 16.50
DEG_LAT_KM = 111.32
DEG_LON_KM = DEG_LAT_KM * math.cos(math.radians(LAT_C))


def latlon_to_xy_km(lat, lon):
    """Equirectangular: simple flat-Earth projection in km from centre."""
    x = (lon - LON_C) * DEG_LON_KM
    y = (lat - LAT_C) * DEG_LAT_KM
    return x, y


# %% [Load the catalog]

cat_path = Path(__file__).parent.parent / "data" / "vienna_basin_catalog.csv"
print(f"Loading catalog from {cat_path}")
events = []
with open(cat_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            events.append({
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "magnitude": float(row["magnitude"]),
                "datetime": row["datetime_utc"],
                "region": row.get("region", ""),
                "source": row.get("source", ""),
            })
        except (ValueError, KeyError):
            continue
print(f"  loaded {len(events)} events")
print()


# %% [Project to xy in km]

X = np.array([[*latlon_to_xy_km(e["lat"], e["lon"])] for e in events])
mags = np.array([e["magnitude"] for e in events])

aspern_xy = np.array(latlon_to_xy_km(ASPERN_LAT, ASPERN_LON))
ebreichsdorf_xy = np.array(latlon_to_xy_km(EBREICHSDORF_LAT, EBREICHSDORF_LON))


# %% [DBSCAN sweep]

print("=== DBSCAN clustering (eps in km, min_samples) ===")
print(f"  {'eps[km]':>8} {'min_s':>6} {'#clusters':>10} {'#noise':>7} "
      f"{'largest':>8}")

dbscan_results = []
for eps in (3.0, 5.0, 8.0, 12.0):
    for ms in (3, 5, 8):
        labels = DBSCAN(eps=eps, min_samples=ms).fit_predict(X)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int((labels == -1).sum())
        sizes = [int((labels == k).sum()) for k in set(labels) if k >= 0]
        largest = max(sizes) if sizes else 0
        print(f"  {eps:>8.1f} {ms:>6d} {n_clusters:>10d} {n_noise:>7d} "
              f"{largest:>8d}")
        dbscan_results.append((eps, ms, labels))
print()


# %% [Pick a canonical DBSCAN setting and analyse]

# eps=8km, min_samples=5 gives a sensible coarse clustering for the Vienna
# Basin: large enough to merge the Ebreichsdorf cluster across event noise,
# small enough to keep distinct regional sources separate.
EPS_CANONICAL = 8.0
MS_CANONICAL = 5
labels = DBSCAN(eps=EPS_CANONICAL, min_samples=MS_CANONICAL).fit_predict(X)


print(f"=== Canonical DBSCAN (eps={EPS_CANONICAL} km, min_samples={MS_CANONICAL}) ===")
unique_labels = sorted(set(labels))
for k in unique_labels:
    mask = labels == k
    n = int(mask.sum())
    if n == 0:
        continue
    centroid_x = X[mask, 0].mean()
    centroid_y = X[mask, 1].mean()
    # Convert centroid back to lat/lon
    cent_lat = LAT_C + centroid_y / DEG_LAT_KM
    cent_lon = LON_C + centroid_x / DEG_LON_KM
    mag_mean = mags[mask].mean()
    mag_max = mags[mask].max()
    label_name = "NOISE" if k == -1 else f"C{k}"
    print(f"  {label_name:>6}: n={n:3d}  centroid=({cent_lat:.3f}N,"
          f" {cent_lon:.3f}E)  Mmean={mag_mean:.2f}  Mmax={mag_max:.1f}")
print()


# %% [Are AFS-proximal events in the same cluster as Ebreichsdorf?]

def closest_event_to(target_xy, max_n=20):
    d = np.linalg.norm(X - target_xy, axis=1)
    order = np.argsort(d)[:max_n]
    return order, d[order]


print("=== AFS-proximal vs Ebreichsdorf cluster identity ===")
asp_order, asp_d = closest_event_to(aspern_xy, max_n=10)
ebr_order, ebr_d = closest_event_to(ebreichsdorf_xy, max_n=10)

print("Closest 10 events to Aspern (planned site):")
for i in range(10):
    idx = asp_order[i]
    print(f"  {events[idx]['datetime'][:10]}  M{mags[idx]:>4.1f}  "
          f"at {asp_d[i]:>5.1f} km  cluster={labels[idx]}  "
          f"{events[idx]['region'][:40]}")
print("Closest 10 events to Ebreichsdorf (busy zone):")
for i in range(10):
    idx = ebr_order[i]
    print(f"  {events[idx]['datetime'][:10]}  M{mags[idx]:>4.1f}  "
          f"at {ebr_d[i]:>5.1f} km  cluster={labels[idx]}  "
          f"{events[idx]['region'][:40]}")
print()


# %% [Build cluster identity table for the report]

asp_clusters = set(labels[asp_order])
ebr_clusters = set(labels[ebr_order])
shared = asp_clusters & ebr_clusters
shared_non_noise = {c for c in shared if c != -1}
print(f"Cluster labels of 10 nearest events to Aspern:        {sorted(asp_clusters)}")
print(f"Cluster labels of 10 nearest events to Ebreichsdorf:  {sorted(ebr_clusters)}")
print(f"Shared cluster labels (excluding noise):              {sorted(shared_non_noise)}")
if not shared_non_noise:
    print("  -> Aspern and Ebreichsdorf events do NOT share a DBSCAN cluster.")
    print("     Their seismicity is statistically separated at this eps.")
else:
    print("  -> Aspern and Ebreichsdorf events share at least one cluster.")
    print(f"     Shared: {sorted(shared_non_noise)}")
print()


# %% [k-means for comparison]

print("=== k-means clustering (k = 2, 3, 4) ===")
for k in (2, 3, 4):
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
    labels_km = km.labels_
    if k > 1:
        s = silhouette_score(X, labels_km)
    else:
        s = float("nan")
    print(f"  k={k}: silhouette={s:.3f}")
    for kk in range(k):
        mask = labels_km == kk
        cent_x, cent_y = X[mask].mean(axis=0)
        cent_lat = LAT_C + cent_y / DEG_LAT_KM
        cent_lon = LON_C + cent_x / DEG_LON_KM
        # Which named site is closest?
        d_asp = math.hypot(cent_x - aspern_xy[0], cent_y - aspern_xy[1])
        d_ebr = math.hypot(cent_x - ebreichsdorf_xy[0], cent_y - ebreichsdorf_xy[1])
        which = "Aspern-area" if d_asp < d_ebr else "Ebreichsdorf-area"
        print(f"    C{kk}: n={int(mask.sum()):3d}  "
              f"centroid=({cent_lat:.3f}N, {cent_lon:.3f}E)  "
              f"d_Aspern={d_asp:.1f}km  d_Ebrei={d_ebr:.1f}km  ({which})")
print()


# %% [Quantitative test: are Aspern-area events a distinct population?]

# Define Aspern-area as 15 km radius (the T2 inner monitoring threshold),
# Ebreichsdorf-area as 15 km radius. Compare magnitude distributions.
d_asp_all = np.linalg.norm(X - aspern_xy, axis=1)
d_ebr_all = np.linalg.norm(X - ebreichsdorf_xy, axis=1)
mask_asp = d_asp_all <= 15
mask_ebr = d_ebr_all <= 15

print("=== Aspern 15-km zone vs Ebreichsdorf 15-km zone ===")
print(f"  Aspern zone:        n={int(mask_asp.sum())}  "
      f"Mmean={mags[mask_asp].mean() if mask_asp.any() else 0:.2f}  "
      f"Mmax={mags[mask_asp].max() if mask_asp.any() else 0:.1f}")
print(f"  Ebreichsdorf zone:  n={int(mask_ebr.sum())}  "
      f"Mmean={mags[mask_ebr].mean() if mask_ebr.any() else 0:.2f}  "
      f"Mmax={mags[mask_ebr].max() if mask_ebr.any() else 0:.1f}")
print(f"  Overlap (both 15-km zones): {int((mask_asp & mask_ebr).sum())}")
print(f"  Aspern - Ebreichsdorf separation: "
      f"{np.linalg.norm(aspern_xy - ebreichsdorf_xy):.1f} km")
print()


# %% [Save cluster assignments]

out_dir = Path(__file__).parent.parent / "data"
out_csv = out_dir / "vienna_basin_catalog_clustered.csv"
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["datetime_utc", "lat", "lon", "magnitude", "source",
                "region", "dbscan_cluster",
                "dist_km_aspern", "dist_km_ebreichsdorf"])
    for i, e in enumerate(events):
        w.writerow([e["datetime"], e["lat"], e["lon"], e["magnitude"],
                    e["source"], e["region"], int(labels[i]),
                    f"{d_asp_all[i]:.2f}", f"{d_ebr_all[i]:.2f}"])
print(f"Wrote {out_csv}")


# %% [Export numpy arrays for figure script reuse]

np.savez(out_dir / "vienna_basin_xy.npz",
         X=X, mags=mags, labels=labels,
         aspern_xy=aspern_xy, ebreichsdorf_xy=ebreichsdorf_xy,
         lat_c=LAT_C, lon_c=LON_C,
         deg_lat_km=DEG_LAT_KM, deg_lon_km=DEG_LON_KM)
print(f"Wrote {out_dir / 'vienna_basin_xy.npz'} for the figure script.")
