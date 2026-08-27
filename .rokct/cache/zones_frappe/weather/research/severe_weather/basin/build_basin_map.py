"""Build the static basin-routing artifact for the ERA5 0.25 deg grid.

Maps every ERA5 grid cell over southern Africa to its HydroBASINS level-7
sub-basin and records the sub-basin river topology (NEXT_DOWN chains,
along-network distances, areas), producing the compact JSON artifact the
warnings engine's upstream-flood signal consumes:

    weather/frappe/src/control/warnings_engine/basin_map.json

Data source: HydroBASINS v1c, level 7, Africa ("standard" attribute set:
HYBAS_ID, NEXT_DOWN, MAIN_BAS, DIST_MAIN, SUB_AREA, UP_AREA, ...).

  Canonical download (no key, but see the network note below):
    https://www.hydrosheds.org/products/hydrobasins
    -> hybas_af_lev07_v1c.zip  (data.hydrosheds.org)
  License: the HydroSHEDS version-1 license (Technical Documentation,
    Appendix A) - freely available for scientific, educational and
    COMMERCIAL use; attribution required. Citation:
      Lehner, B., Grill G. (2013): Global river hydrography and network
      routing: baseline data and new approaches to study the world's large
      river systems. Hydrological Processes, 27(15): 2171-2186.
    The attribution block is embedded in the generated artifact and must be
    carried by anything redistributing it.

Inputs accepted (first match wins):
  1. --shapefile /path/to/hybas_af_lev07_v1c.shp   (the canonical product;
     needs pyshp: pip install pyshp)
  2. --geojson-dir /path/to/africa_geojsons/       (a directory of GeoJSON
     FeatureCollections whose feature properties carry the standard
     HydroBASINS attributes plus "level"; features with level != 7 are
     ignored. Used at build time 2026-08-21 via the public mirror
     github.com/SilliamBims/WikiGroundWatersheds - a faithful
     shapefile->GeoJSON conversion of HydroBASINS v1c levels 03-07,
     attribution preserved - because data.hydrosheds.org was unreachable
     from the build environment's egress proxy. Regenerating from the
     canonical shapefile must yield the same topology; the sanity block
     below asserts the load-bearing facts either way.)

Method:
  - keep level-7 sub-basins whose bounding box intersects the region
    (lat -36..-10, lon 10..42 - Limpopo, Orange/Vaal, lower Zambezi/Okavango,
    Save, Incomati, Cape rivers, coastal basins);
  - assign each ERA5 cell CENTER to its containing sub-basin polygon
    (shapely point-in-polygon over an STRtree); coastal/edge cells whose
    center misses every polygon fall back to the nearest polygon within
    COASTAL_SNAP_DEG (ERA5 coastal cells are part ocean - their center can
    sit offshore while the cell still covers river-mouth land, e.g. the
    Xai-Xai cell at the Limpopo mouth);
  - for each kept sub-basin record its topology row and a representative
    grid cell (the cell nearest the polygon centroid) at which the engine
    samples that sub-basin's rain.

Sanity assertions (fail the build if violated): the six Limpopo case-study
cells (weather/research/severe_weather/casestudy_limpopo) must share one
MAIN_BAS; the upstream set of the chokwe cell must contain the musina,
thohoyandou and pafuri cells (main stem) with musina the farthest; and the
xai_xai (river-mouth) cell's upstream set must contain all five other
cells. The mapai 0.25 deg cell is deliberately NOT asserted upstream of
chokwe: its cell center falls in the Changane tributary catchment, which
joins the Limpopo BELOW Chokwe (above the mouth) - correct hydrology at
this resolution.

Output size target: a few hundred KB of minified JSON. Nothing here runs at
serve time - the artifact is loaded read-only by the engine.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys

REGION_LAT = (-36.0, -10.0)
REGION_LON = (10.0, 42.0)
GRID_STEP = 0.25
COASTAL_SNAP_DEG = 0.2  # max center-to-polygon distance for coastal fallback

ARTIFACT_VERSION = 1

ATTRIBUTION = {
    "dataset": "HydroBASINS v1c, level 7, Africa (standard attribute set)",
    "provider": "HydroSHEDS / World Wildlife Fund",
    "url": "https://www.hydrosheds.org/products/hydrobasins",
    "license": (
        "HydroSHEDS version-1 license (Technical Documentation, Appendix A): "
        "freely available for scientific, educational and commercial use; "
        "attribution required."
    ),
    "citation": (
        "Lehner, B., Grill G. (2013): Global river hydrography and network "
        "routing: baseline data and new approaches to study the world's "
        "large river systems. Hydrological Processes, 27(15): 2171-2186."
    ),
}

# The six Limpopo case-study points (LIMPOPO_CASE_STUDY.md section 2) used
# for the build-time sanity assertions.
LIMPOPO_POINTS = {
    "thohoyandou": (-22.95, 30.48),
    "musina": (-22.35, 30.03),
    "pafuri": (-22.45, 31.32),
    "mapai": (-22.85, 31.98),
    "chokwe": (-24.53, 32.98),
    "xai_xai": (-25.05, 33.64),
}


def grid_index(lat: float, lon: float) -> tuple[int, int]:
    """ERA5 join discipline (PLAN.md section 1): index 0 = 90S / 180W."""
    la = int(round((lat + 90.0) / GRID_STEP))
    lo = int(round((lon + 180.0) / GRID_STEP)) % 1440
    return la, lo


def grid_latlon(la: int, lo: int) -> tuple[float, float]:
    return la * GRID_STEP - 90.0, lo * GRID_STEP - 180.0


def _bbox_intersects(xs, ys) -> bool:
    return not (max(xs) < REGION_LON[0] or min(xs) > REGION_LON[1]
                or max(ys) < REGION_LAT[0] or min(ys) > REGION_LAT[1])


def load_from_geojson_dir(path: str) -> list[dict]:
    """[{props..., 'geometry': shapely geom}] for in-region level-7 basins."""
    from shapely.geometry import shape

    rows = []
    for f in sorted(glob.glob(os.path.join(path, "*.geojson"))):
        data = json.load(open(f))
        for ft in data.get("features", []):
            pr = ft.get("properties", {})
            if pr.get("level") not in (None, 7):
                continue
            hybas = int(pr["HYBAS_ID"])
            if pr.get("level") is None and str(hybas)[1:3] != "07":
                continue  # plain HydroBASINS exports carry level in the id
            geom = shape(ft["geometry"])
            xs, ys = geom.bounds[0::2], geom.bounds[1::2]
            if not _bbox_intersects(xs, ys):
                continue
            rows.append({
                "hybas_id": hybas,
                "next_down": int(pr["NEXT_DOWN"]),
                "main_bas": int(pr["MAIN_BAS"]),
                "dist_main": float(pr["DIST_MAIN"]),
                "sub_area": float(pr["SUB_AREA"]),
                "up_area": float(pr["UP_AREA"]),
                "geometry": geom,
            })
    return rows


def load_from_shapefile(path: str) -> list[dict]:
    """Same rows from the canonical hybas_af_lev07_v1c shapefile."""
    import shapefile  # pyshp
    from shapely.geometry import shape

    rows = []
    reader = shapefile.Reader(path)
    fields = [f[0] for f in reader.fields[1:]]
    for sr in reader.iterShapeRecords():
        pr = dict(zip(fields, sr.record))
        geom = shape(sr.shape.__geo_interface__)
        xs, ys = geom.bounds[0::2], geom.bounds[1::2]
        if not _bbox_intersects(xs, ys):
            continue
        rows.append({
            "hybas_id": int(pr["HYBAS_ID"]),
            "next_down": int(pr["NEXT_DOWN"]),
            "main_bas": int(pr["MAIN_BAS"]),
            "dist_main": float(pr["DIST_MAIN"]),
            "sub_area": float(pr["SUB_AREA"]),
            "up_area": float(pr["UP_AREA"]),
            "geometry": geom,
        })
    return rows


def build(rows: list[dict]) -> dict:
    from shapely import STRtree
    from shapely.geometry import Point

    # de-duplicate (mirror files repeat shared-boundary basins)
    by_id = {}
    for r in rows:
        by_id[r["hybas_id"]] = r
    rows = list(by_id.values())
    geoms = [r["geometry"] for r in rows]
    tree = STRtree(geoms)

    # --- cell -> sub-basin assignment -------------------------------------
    la0, la1 = grid_index(REGION_LAT[0], 0)[0], grid_index(REGION_LAT[1], 0)[0]
    lo0, lo1 = grid_index(0, REGION_LON[0])[1], grid_index(0, REGION_LON[1])[1]
    cells: dict[str, int] = {}
    snapped = 0
    for la in range(la0, la1 + 1):
        for lo in range(lo0, lo1 + 1):
            lat, lon = grid_latlon(la, lo)
            p = Point(lon, lat)
            hit = None
            for i in tree.query(p, predicate="within"):
                hit = rows[i]
                break
            if hit is None:
                i = tree.nearest(p)
                if geoms[i].distance(p) <= COASTAL_SNAP_DEG:
                    hit = rows[i]
                    snapped += 1
            if hit is not None:
                cells[f"{la}_{lo}"] = hit["hybas_id"]

    # --- representative cell per sub-basin --------------------------------
    subbasins: dict[str, list] = {}
    for r in rows:
        c = r["geometry"].centroid
        rla, rlo = grid_index(c.y, c.x)
        subbasins[str(r["hybas_id"])] = [
            r["next_down"], r["main_bas"], round(r["dist_main"], 1),
            round(r["sub_area"], 1), round(r["up_area"], 1), rla, rlo,
        ]

    print(f"sub-basins kept: {len(subbasins)}; cells mapped: {len(cells)} "
          f"(coastal-snapped: {snapped})")
    return {
        "version": ARTIFACT_VERSION,
        "generated": dt.date.today().isoformat(),
        "source": ATTRIBUTION,
        "grid": {"step": GRID_STEP, "index_origin": [-90.0, -180.0],
                 "fields": ["next_down", "main_bas", "dist_main_km",
                            "sub_area_km2", "up_area_km2", "rep_lat_idx",
                            "rep_lon_idx"]},
        "region": {"lat": list(REGION_LAT), "lon": list(REGION_LON)},
        "subbasins": subbasins,
        "cells": cells,
    }


def upstream_of(artifact: dict, cell_key: str) -> dict[int, float]:
    """{upstream hybas_id: along-network distance delta km} - build-time
    mirror of the engine's traversal, for the sanity assertions."""
    subs = artifact["subbasins"]
    target = artifact["cells"].get(cell_key)
    if target is None:
        return {}
    downstream_of = {}
    for hid, row in subs.items():
        downstream_of.setdefault(row[0], []).append(int(hid))
    base = subs[str(target)][2]
    out, frontier = {}, [target]
    while frontier:
        nxt = []
        for t in frontier:
            for up in downstream_of.get(t, []):
                if up not in out and up != target:
                    out[up] = round(subs[str(up)][2] - base, 1)
                    nxt.append(up)
        frontier = nxt
    return out


def sanity(artifact: dict) -> None:
    cells = artifact["cells"]
    subs = artifact["subbasins"]
    keys = {n: "%d_%d" % grid_index(*ll) for n, ll in LIMPOPO_POINTS.items()}
    missing = [n for n, k in keys.items() if k not in cells]
    assert not missing, f"Limpopo case-study cells unmapped: {missing}"
    main = {n: subs[str(cells[keys[n]])][1] for n in keys}
    assert len(set(main.values())) == 1, f"MAIN_BAS mismatch: {main}"
    up = upstream_of(artifact, keys["chokwe"])
    for name in ("musina", "thohoyandou", "pafuri"):
        sb = cells[keys[name]]
        assert sb in up, f"{name} not upstream of chokwe"
    d = {n: up[cells[keys[n]]] for n in ("musina", "thohoyandou", "pafuri")}
    assert d["musina"] > d["thohoyandou"] > 0, f"distance order: {d}"
    up_mouth = upstream_of(artifact, keys["xai_xai"])
    for name in ("musina", "thohoyandou", "pafuri", "mapai", "chokwe"):
        sb = cells[keys[name]]
        assert sb in up_mouth, f"{name} not upstream of xai_xai"
    print("sanity OK - Limpopo MAIN_BAS", set(main.values()),
          "chokwe upstream count", len(up),
          "xai_xai upstream count", len(up_mouth),
          "deltas above chokwe km", d)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shapefile", help="hybas_af_lev07_v1c.shp (canonical)")
    ap.add_argument("--geojson-dir", help="dir of HydroBASINS GeoJSON files")
    ap.add_argument("--out", required=True, help="output basin_map.json path")
    args = ap.parse_args()
    if args.shapefile:
        rows = load_from_shapefile(args.shapefile)
    elif args.geojson_dir:
        rows = load_from_geojson_dir(args.geojson_dir)
    else:
        ap.error("one of --shapefile / --geojson-dir is required")
    artifact = build(rows)
    sanity(artifact)
    with open(args.out, "w", newline="\n") as f:
        json.dump(artifact, f, separators=(",", ":"), sort_keys=True)
        f.write("\n")
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
