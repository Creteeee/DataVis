# -*- coding: utf-8 -*-
"""Summarize herbaceous vs woody species by school (grouped by district).

Input:  Plants_Shanghai_Translated.xlsx
Output: growthform_by_school.csv / growthform_by_school.md

Rule: shrubs + trees are counted as woody; herbs as herbaceous.
Counts are unique species (ScientificName) per school.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
SRC = BASE / "Plants_Shanghai_Translated.xlsx"
OUT_CSV = BASE / "growthform_by_school.csv"
OUT_MD = BASE / "growthform_by_school.md"
OUT_SNIPPET = BASE / "growthform_by_school_ascii_snippet.md"


def _first_present(df: pd.DataFrame, candidates: list[str]) -> str:
    cols = {str(c).strip(): str(c) for c in df.columns}
    for c in candidates:
        if c in cols:
            return cols[c]
    raise KeyError(f"缺少列：需要其一 {candidates}，但现有列为 {list(df.columns)}")


def normalize_growth_form(x: object) -> str:
    s = str(x).strip()
    if not s or s.lower() in ("nan", "none"):
        return ""
    s_low = s.lower()
    if s_low in ("herb", "草本"):
        return "Herb"
    if s_low in ("shrub", "灌木"):
        return "Shrub"
    if s_low in ("tree", "乔木"):
        return "Tree"
    return s


def stacked_bar(herb_ratio: float, width: int = 24) -> str:
    herb_ratio = 0.0 if herb_ratio != herb_ratio else float(herb_ratio)  # NaN-safe
    herb_ratio = max(0.0, min(1.0, herb_ratio))
    h = int(round(width * herb_ratio))
    w = width - h
    return ("H" * h) + ("W" * w)


def block_bar(p: float, width: int = 20, fill: str = "█", empty: str = "░") -> str:
    """Return a fixed-width bar. Uses floor like the existing nativeness preview."""
    if p != p:  # NaN-safe
        p = 0.0
    p = max(0.0, min(1.0, float(p)))
    k = int(p * width)
    return (fill * k) + (empty * (width - k))


def build_summary(xlsx_path: Path) -> pd.DataFrame:
    xl = pd.ExcelFile(xlsx_path)
    frames: list[pd.DataFrame] = []
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)

    # Prefer Chinese columns if present (to match existing framework doc style)
    col_school = _first_present(full, ["地点", "Locality"])
    col_district = _first_present(full, ["区", "District"])
    col_growth = _first_present(full, ["生长型", "GrowthForm"])
    col_species = _first_present(full, ["ScientificName", "中文名"])

    df2 = pd.DataFrame(
        {
            "District": full[col_district].astype(str).str.strip(),
            "School": full[col_school].astype(str).str.strip(),
            "GrowthForm": full[col_growth].map(normalize_growth_form),
            "ScientificName": full[col_species].astype(str).str.strip(),
        }
    )

    # Clean
    df2 = df2[(df2["District"] != "") & (df2["School"] != "")]
    df2 = df2[df2["ScientificName"].notna() & (df2["ScientificName"] != "")]

    df2["WoodyFlag"] = df2["GrowthForm"].isin(["Tree", "Shrub"])
    df2["HerbFlag"] = df2["GrowthForm"].isin(["Herb"])

    # Unique species per school per growth category
    herb = (
        df2[df2["HerbFlag"]]
        .groupby(["District", "School"])["ScientificName"]
        .nunique()
        .rename("Herb_species")
    )
    woody = (
        df2[df2["WoodyFlag"]]
        .groupby(["District", "School"])["ScientificName"]
        .nunique()
        .rename("Woody_species")
    )
    total = (
        df2.groupby(["District", "School"])["ScientificName"]
        .nunique()
        .rename("Total_species")
    )

    out = pd.concat([herb, woody, total], axis=1).fillna(0).reset_index()
    out[["Herb_species", "Woody_species", "Total_species"]] = out[
        ["Herb_species", "Woody_species", "Total_species"]
    ].astype(int)

    out["Herb_ratio"] = out["Herb_species"] / out["Total_species"].where(out["Total_species"] != 0, pd.NA)
    out["Woody_ratio"] = out["Woody_species"] / out["Total_species"].where(out["Total_species"] != 0, pd.NA)
    out["Bar(H=草本,W=木本)"] = out["Herb_ratio"].fillna(0).map(lambda r: stacked_bar(float(r)))

    out = out.sort_values(["District", "Total_species", "Woody_species", "Herb_species", "School"], ascending=[True, False, False, False, True])
    return out


def to_framework_ascii_snippet(df: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append("#### 字符柱状图示意：草本 vs 木本（每条为 20 格，█=占比） | ASCII bar preview: Herb vs Woody (20 blocks)")
    lines.append("")
    lines.append("*按校（物种占比；木本=灌木+乔木）*")
    lines.append("")
    preferred = ["闵行区", "杨浦区", "奉贤区", "宝山区"]
    districts = list(dict.fromkeys(df["District"].tolist()))
    districts = sorted(
        districts,
        key=lambda d: (preferred.index(d) if d in preferred else 10_000 + hash(d)),
    )
    for district in districts:
        g = df[df["District"] == district]
        lines.append(f"**{district}**")
        lines.append("")
        for _, r in g.iterrows():
            t = int(r["Total_species"])
            hr = float(r["Herb_ratio"]) if pd.notna(r["Herb_ratio"]) else 0.0
            wr = float(r["Woody_ratio"]) if pd.notna(r["Woody_ratio"]) else 0.0
            lines.append(f"- **{str(r['School'])}**（物种 {t}）")
            lines.append(f"  - 草本 ` {hr*100:.1f}%` `{block_bar(hr)}`")
            lines.append(f"  - 木本 ` {wr*100:.1f}%` `{block_bar(wr)}`")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_markdown_grouped(df: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append("# 上海校园：草本 vs 木本（灌木+乔木）按学校统计")
    lines.append("")
    lines.append("说明：")
    lines.append("- 统计口径：每个学校内 **不同学名（ScientificName）** 的数量（去重）。")
    lines.append("- 木本=灌木+乔木；草本=Herb。")
    lines.append("- 条形图：`H`=草本比例，`W`=木本比例（总宽 24）。")
    lines.append("")
    for district, g in df.groupby("District", sort=False):
        lines.append(f"## {district}")
        lines.append("")
        lines.append("| 学校 | 草本(种) | 木本(种) | 总计(种) | 草本比例 | 木本比例 | 条形图 |")
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for _, r in g.iterrows():
            hr = float(r["Herb_ratio"]) if pd.notna(r["Herb_ratio"]) else 0.0
            wr = float(r["Woody_ratio"]) if pd.notna(r["Woody_ratio"]) else 0.0
            lines.append(
                "| {school} | {h} | {w} | {t} | {hr:.1%} | {wr:.1%} | `{bar}` |".format(
                    school=str(r["School"]),
                    h=int(r["Herb_species"]),
                    w=int(r["Woody_species"]),
                    t=int(r["Total_species"]),
                    hr=hr,
                    wr=wr,
                    bar=str(r["Bar(H=草本,W=木本)"]),
                )
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="按区/学校统计草本与木本（灌木+乔木）数量与比例，并输出字符条形图。")
    ap.add_argument("--src", type=Path, default=SRC, help="输入 xlsx 路径（默认 Plants_Shanghai_Translated.xlsx）")
    ap.add_argument("--out-csv", type=Path, default=OUT_CSV, help="输出 CSV 路径")
    ap.add_argument("--out-md", type=Path, default=OUT_MD, help="输出 Markdown 路径")
    ap.add_argument("--out-snippet", type=Path, default=OUT_SNIPPET, help="输出可粘贴到框架文档的 ASCII 片段（md）")
    args = ap.parse_args()

    if not args.src.exists():
        raise SystemExit(f"缺少输入文件：{args.src}")

    summary = build_summary(args.src)
    summary.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    args.out_md.write_text(to_markdown_grouped(summary), encoding="utf-8")
    args.out_snippet.write_text(to_framework_ascii_snippet(summary), encoding="utf-8")
    print("Wrote:", args.out_csv)
    print("Wrote:", args.out_md)
    print("Wrote:", args.out_snippet)


if __name__ == "__main__":
    main()

