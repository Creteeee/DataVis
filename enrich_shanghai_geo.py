# -*- coding: utf-8 -*-
"""Add District, Longitude, Latitude after Locality in Plants/Birds Shanghai CSVs.

Coordinates: WGS84 decimal degrees, approximate centroid per campus/park (mapping below).
If the target CSV is open in another program and cannot be overwritten, outputs
``*_enriched.csv`` in the same folder instead.
"""
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "Plants&GreenSpace" / "CampusGreenSpace"

# Locality (exact match) -> (District_en, longitude, latitude)
LOCALITY_GEO = {
    # Plants — campuses
    "East China Normal University, Minhang Campus": (
        "Minhang District",
        121.4531,
        31.0318,
    ),
    "Fudan University, Handan Campus": ("Yangpu District", 121.5038, 31.2985),
    "Fudan University, Jiangwan Campus": ("Yangpu District", 121.5115, 31.3388),
    "Shanghai Institute of Technology": ("Fengxian District", 121.4996, 30.8877),
    "Shanghai Jiao Tong University": ("Minhang District", 121.4379, 31.0249),
    "Shanghai University, Baoshan Campus": ("Baoshan District", 121.3912, 31.3198),
    "Tongji University": ("Yangpu District", 121.5064, 31.2825),
    # Birds — parks / gardens
    "Shanghai Bay Forest Park": ("Fengxian District", 121.7265, 30.8812),
    "Shanghai Botanical Garden": ("Xuhui District", 121.4714, 31.1489),
    "Shanghai Century Park": ("Pudong New Area", 121.5547, 31.2165),
    "Shanghai Chenshan Botanical Garden": ("Songjiang District", 121.1789, 31.0715),
    "Shanghai Gongqing Forest Park": ("Yangpu District", 121.5572, 31.3135),
    # Interpreted as Pudong Binjiang riverside forest park (滨江森林公园)
    "Shanghai Riviera Forest Park": ("Pudong New Area", 121.5792, 31.4185),
}


def enrich_file(name: str) -> Path:
    path = BASE / name
    if not path.is_file():
        raise SystemExit(f"Missing {path}")

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if "Locality" not in fieldnames:
            raise SystemExit(f"{name}: no Locality column")
        insert_at = fieldnames.index("Locality") + 1
        new_fields = (
            fieldnames[:insert_at]
            + ["District", "Longitude", "Latitude"]
            + fieldnames[insert_at:]
        )
        rows_out = []
        for row in reader:
            loc = (row.get("Locality") or "").strip()
            geo = LOCALITY_GEO.get(loc)
            if geo is None:
                raise SystemExit(f"{name}: unmapped Locality: {loc!r}")
            d, lon, lat = geo
            row["District"] = d
            row["Longitude"] = f"{lon:.6f}"
            row["Latitude"] = f"{lat:.6f}"
            rows_out.append(row)

    tmp = path.with_suffix(".tmp.csv")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=new_fields)
        w.writeheader()
        w.writerows(rows_out)

    fallback = path.with_name(path.stem + "_enriched.csv")
    try:
        tmp.replace(path)
        written = path
        if fallback.is_file():
            try:
                fallback.unlink()
            except OSError:
                pass
    except OSError:
        shutil.move(str(tmp), str(fallback))
        written = fallback

    return written


def main():
    p1 = enrich_file("Plants_Shanghai.csv")
    p2 = enrich_file("Birds_Shanghai.csv")
    print(f"Plants -> {p1}")
    print(f"Birds    -> {p2}")


if __name__ == "__main__":
    main()
