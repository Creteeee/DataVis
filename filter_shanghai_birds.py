# -*- coding: utf-8 -*-
"""Filter ERDP bird list for Shanghai — same locality rules as Plants_Shanghai."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "Plants&GreenSpace" / "CampusGreenSpace" / "ERDP-2021-02.2.1-Bird_List.csv"
OUT = ROOT / "Plants&GreenSpace" / "CampusGreenSpace" / "Birds_Shanghai.csv"
NOTE = ROOT / "Plants&GreenSpace" / "CampusGreenSpace" / "Birds_Shanghai_filter_note.txt"


def locality_is_shanghai(loc: str) -> bool:
    if not loc:
        return False
    s = loc.strip()
    low = s.lower()
    if "shanghai" in low:
        return True
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
        if not fieldnames:
            raise SystemExit("Unexpected CSV schema")
        if "Locality" not in fieldnames:
            raise SystemExit("Expected column Locality")
        rows = list(reader)

    kept = [r for r in rows if locality_is_shanghai(r.get("Locality", "") or "")]

    matched_localities = sorted({(r.get("Locality") or "").strip() for r in kept})

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(kept)

    note_lines = [
        "Birds_Shanghai.csv — filter criteria",
        "",
        f"Source: {SRC.name}",
        f"Rows in source: {len(rows)}",
        f"Rows kept (Shanghai): {len(kept)}",
        "",
        "Same rules as Plants_Shanghai:",
        "  - Locality contains 'Shanghai' (case-insensitive), or",
        "  - starts with 'Fudan University', or",
        "  - starts with 'Tongji University', or",
        "  - starts with 'East China Normal University'",
        "",
        "Unique Locality values included:",
    ]
    note_lines.extend(f"  - {x}" for x in matched_localities)

    NOTE.write_text("\n".join(note_lines), encoding="utf-8")

    print(f"Kept {len(kept)} / {len(rows)} rows -> {OUT.name}")
    print(f"Note -> {NOTE.name}")


if __name__ == "__main__":
    main()
