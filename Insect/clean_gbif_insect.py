# -*- coding: utf-8 -*-
"""将 GBIF 下载的昆虫 occurrence TSV 整理为易读的表格（中文列名、按日期排序）。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
SRC = BASE / "Insect.csv"
OUT_XLSX = BASE / "Insect_阅读版.xlsx"

BASIS_ZH = {
    "PRESERVED_SPECIMEN": "馆藏标本",
    "HUMAN_OBSERVATION": "人工观测",
    "MATERIAL_SAMPLE": "材料样品",
    "OBSERVATION": "观测记录",
    "FOSSIL_SPECIMEN": "化石标本",
    "LIVING_SPECIMEN": "活体标本",
}


def _basis_zh(v: object) -> str:
    if pd.isna(v) or str(v).strip() == "":
        return ""
    s = str(v).strip()
    return BASIS_ZH.get(s, s)


def _event_series(df: pd.DataFrame) -> pd.Series:
    t = pd.to_datetime(df["eventDate"], errors="coerce", utc=False)
    fallback = pd.to_datetime(
        dict(year=df["year"], month=df["month"].fillna(1), day=df["day"].fillna(1)),
        errors="coerce",
    )
    return t.fillna(fallback)


def _display_date(row: pd.Series) -> str:
    if pd.notna(row.get("eventDate")) and str(row["eventDate"]).strip() not in ("", "nan"):
        return str(row["eventDate"]).strip()
    if pd.notna(row.get("year")):
        try:
            y = int(row["year"])
            m = int(row["month"]) if pd.notna(row.get("month")) else 1
            d = int(row["day"]) if pd.notna(row.get("day")) else 1
            return f"{y:04d}-{m:02d}-{d:02d}"
        except (ValueError, TypeError):
            return ""
    return ""


def build_reading_table(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["_sort_dt"] = _event_series(work)
    work["采集或观察日期"] = work.apply(_display_date, axis=1)
    work = work.sort_values("_sort_dt", ascending=False, na_position="last")

    return pd.DataFrame(
        {
            "GBIF记录ID": work["gbifID"],
            "学名": work["scientificName"],
            "目": work["order"],
            "科": work["family"],
            "属": work["genus"],
            "GBIF种名字段": work["species"],
            "分类阶元": work["taxonRank"],
            "记录类型": work["basisOfRecord"].map(_basis_zh),
            "国家地区代码": work["countryCode"],
            "省_直辖市": work["stateProvince"],
            "地点描述": work["locality"],
            "纬度": work["decimalLatitude"],
            "经度": work["decimalLongitude"],
            "坐标不确定性_米": work["coordinateUncertaintyInMeters"],
            "采集或观察日期": work["采集或观察日期"],
            "出现状态": work["occurrenceStatus"],
            "个体数": work["individualCount"],
            "机构代码": work["institutionCode"],
            "馆藏或项目代码": work["collectionCode"],
            "标本或样本号": work["catalogNumber"],
            "原始记录ID": work["occurrenceID"],
            "记录人": work["recordedBy"],
            "鉴定人": work["identifiedBy"],
            "鉴定日期": work["dateIdentified"],
            "数据许可": work["license"],
            "媒体类型": work["mediaType"],
            "GBIF质量提示": work["issue"].fillna("").astype(str).str.replace(";", "；"),
        }
    )


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"找不到源文件：{SRC}")

    raw = pd.read_csv(SRC, sep="\t", encoding="utf-8", low_memory=False)
    reading = build_reading_table(raw)

    meta = pd.DataFrame(
        {
            "说明": [
                "本表由 GBIF occurrence 导出整理，原始文件为制表符分隔（TSV），在 Excel 中请用「数据→自文本」并选择制表符。",
                "记录类型等字段已部分译为中文；学名以 GBIF scientificName 为准。",
                "日期优先使用 eventDate；缺失时用 year/month/day 组合。",
                "GBIF质量提示：分号已改为中文分号便于阅读。",
            ]
        }
    )

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        reading.to_excel(writer, sheet_name="昆虫记录", index=False)
        meta.to_excel(writer, sheet_name="使用说明", index=False)

    print(f"已写入 {OUT_XLSX} ，共 {len(reading)} 条记录。")


if __name__ == "__main__":
    main()
