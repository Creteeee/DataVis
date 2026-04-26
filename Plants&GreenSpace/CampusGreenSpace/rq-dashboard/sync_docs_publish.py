# -*- coding: utf-8 -*-
"""
Sync rq-dashboard static site into repository root docs/ for GitHub Pages.
"""

from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]  # .../DataVis/DataVis
DOCS = REPO_ROOT / "docs"

FILES = ["index.html", "app.js", "styles.css"]
DATA_FILES = [
    "campus_summary.json",
    "city_district_summary.json",
    "overlap_taxa.json",
    "rq2_taxa_native_nonnative.json",
    "sankey_district_campus_family.json",
    "treemap_families.json",
    "overlap_family.json",
]


def main() -> None:
    (DOCS / "data").mkdir(parents=True, exist_ok=True)

    for name in FILES:
        shutil.copy2(HERE / name, DOCS / name)

    for name in DATA_FILES:
        shutil.copy2(HERE / "data" / name, DOCS / "data" / name)

    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Published files synced to: {DOCS}")


if __name__ == "__main__":
    main()

