# -*- coding: utf-8 -*-
"""Filter ERDP plant list: rows whose Locality is in Shanghai municipality.

This dataset uses English campus names. Shanghai-related rows include places
without the substring 'Shanghai' (e.g. Fudan University, Tongji University).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "Plants&GreenSpace" / "CampusGreenSpace" / "ERDP-2021-02.4.1-Plant_List.csv"
OUT = ROOT / "Plants&GreenSpace" / "CampusGreenSpace" / "Plants_Shanghai.csv"
NOTE = ROOT / "Plants&GreenSpace" / "CampusGreenSpace" / "Plants_Shanghai_filter_note.txt"


def locality_is_shanghai(loc: str) -> bool:
    if not loc:
        return False
    s = loc.strip()
    low = s.lower()

    # Any locality string that explicitly mentions Shanghai (city / university names).
    if "shanghai" in low:
        return True

    # Major Shanghai campuses that do not contain the word "Shanghai":
    # (verified against unique Locality values in ERDP-2021-02.4.1-Plant_List.csv)
    if s.startswith("Fudan University"):
        return True
    if s.startswith("Tongji University"):
        return True
    if s.startswith("East China Normal University"):
        return True

    return False


def main():
    if not SRC.is_file():
        raise SystemExit(f"Missing source: {SRC}")

    with SRC.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or "Locality" not in fieldnames:
            raise SystemExit("Unexpected CSV schema")
        rows = list(reader)

    kept = [r for r in rows if locality_is_shanghai(r.get("Locality", "") or "")]

    matched_localities = sorted({(r.get("Locality") or "").strip() for r in kept})

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(kept)

    note_lines = [
        "Plants_Shanghai.csv — filter criteria",
        "",
        f"Source: {SRC.name}",
        f"Rows in source: {len(rows)}",
        f"Rows kept (Shanghai): {len(kept)}",
        "",
        "Included when Locality satisfies any of:",
        "  - contains 'Shanghai' (case-insensitive), or",
        "  - starts with 'Fudan University', or",
        "  - starts with 'Tongji University', or",
        "  - starts with 'East China Normal University'",
        "",
        "The last three cover campuses (e.g. Handan / Jiangwan, Minhang) that do not",
        "spell out 'Shanghai'. 'East China Normal University' is used instead of a",
        "loose 'East China' match to avoid catching universities in other provinces.",
        "",
        "Unique Locality values included:",
    ]
    note_lines.extend(f"  - {x}" for x in matched_localities)

    NOTE.write_text("\n".join(note_lines), encoding="utf-8")

    print(f"Kept {len(kept)} / {len(rows)} rows -> {OUT.name}")
    print(f"Note -> {NOTE.name}")


if __name__ == "__main__":
    main()
