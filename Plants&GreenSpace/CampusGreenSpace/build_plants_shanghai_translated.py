# -*- coding: utf-8 -*-
"""Generate Plants_Shanghai_Translated.xlsx from Plants_Shanghai_enriched_District.xlsx."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

BASE = Path(__file__).resolve().parent
SRC = BASE / "Plants_Shanghai_enriched_District.xlsx"
OUT = BASE / "Plants_Shanghai_Translated.xlsx"
CACHE_PATH = BASE / "_plants_zh_name_cache.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DataVis/Education; +https://example.invalid)"}

# 上海区县 / 校区常见地点（与源表英文一致）
DISTRICT_ZH = {
    "Minhang District": "闵行区",
    "Yangpu District": "杨浦区",
    "Fengxian District": "奉贤区",
    "Baoshan District": "宝山区",
}

LOCALITY_ZH = {
    "East China Normal University, Minhang Campus": "华东师范大学（闵行校区）",
    "Shanghai Jiao Tong University": "上海交通大学",
    "Fudan University, Handan Campus": "复旦大学（邯郸校区）",
    "Fudan University, Jiangwan Campus": "复旦大学（江湾校区）",
    "Tongji University": "同济大学",
    "Shanghai Institute of Technology": "上海应用技术大学",
    "Shanghai University, Baoshan Campus": "上海大学（宝山校区）",
}

GROWTH_ZH = {"Tree": "乔木", "Shrub": "灌木", "Herb": "草本"}

TAXON_RANK_ZH = {
    "Species": "种",
    "Cultivar": "栽培品种",
    "Varietas": "变种",
    "Subspecies": "亚种",
    "Forma": "变型",
}

NATIVE_ZH = {"Native": "乡土", "Nonnative": "非乡土"}

# 拉丁科名 -> 中文科名（标准维管植物命名习惯用名）
FAMILY_ZH = {
    "Acanthaceae": "爵床科",
    "Acoraceae": "菖蒲科",
    "Adoxaceae": "五福花科",
    "Aizoaceae": "番杏科",
    "Altingiaceae": "枫香科",
    "Amaranthaceae": "苋科",
    "Amaryllidaceae": "石蒜科",
    "Anacardiaceae": "漆树科",
    "Apiaceae": "伞形科",
    "Apocynaceae": "夹竹桃科",
    "Aquifoliaceae": "冬青科",
    "Araceae": "天南星科",
    "Araliaceae": "五加科",
    "Araucariaceae": "南洋杉科",
    "Arecaceae": "棕榈科",
    "Asparagaceae": "天门冬科",
    "Balsaminaceae": "凤仙花科",
    "Begoniaceae": "秋海棠科",
    "Berberidaceae": "小檗科",
    "Betulaceae": "桦木科",
    "Bignoniaceae": "紫葳科",
    "Boraginaceae": "紫草科",
    "Brassicaceae": "十字花科",
    "Buxaceae": "黄杨科",
    "Cactaceae": "仙人掌科",
    "Calycanthaceae": "蜡梅科",
    "Campanulaceae": "桔梗科",
    "Cannabaceae": "大麻科",
    "Cannaceae": "美人蕉科",
    "Caprifoliaceae": "忍冬科",
    "Caryophyllaceae": "石竹科",
    "Celastraceae": "卫矛科",
    "Ceratophyllaceae": "金鱼藻科",
    "Chloranthaceae": "金粟兰科",
    "Commelinaceae": "鸭跖草科",
    "Compositae": "菊科",
    "Convolvulaceae": "旋花科",
    "Cornaceae": "山茱萸科",
    "Crassulaceae": "景天科",
    "Cucurbitaceae": "葫芦科",
    "Cupressaceae": "柏科",
    "Cycadaceae": "苏铁科",
    "Cyperaceae": "莎草科",
    "Didiereaceae": "刺树科",
    "Ebenaceae": "柿科",
    "Elaeagnaceae": "胡颓子科",
    "Elaeocarpaceae": "杜英科",
    "Equisetaceae": "木贼科",
    "Ericaceae": "杜鹃花科",
    "Eucommiaceae": "杜仲科",
    "Euphorbiaceae": "大戟科",
    "Fagaceae": "壳斗科",
    "Garryaceae": "绞木科",
    "Geraniaceae": "牻牛儿苗科",
    "Ginkgoaceae": "银杏科",
    "Hamamelidaceae": "金缕梅科",
    "Hydrangeaceae": "绣球花科",
    "Hypericaceae": "金丝桃科",
    "Hypoxidaceae": "仙茅科",
    "Iridaceae": "鸢尾科",
    "Juglandaceae": "胡桃科",
    "Lamiaceae": "唇形科",
    "Lauraceae": "樟科",
    "Leguminosae": "豆科",
    "Liliaceae": "百合科",
    "Linderniaceae": "母草科",
    "Lythraceae": "千屈菜科",
    "Magnoliaceae": "木兰科",
    "Malvaceae": "锦葵科",
    "Marantaceae": "竹芋科",
    "Meliaceae": "楝科",
    "Moraceae": "桑科",
    "Musaceae": "芭蕉科",
    "Myricaceae": "杨梅科",
    "Myrtaceae": "桃金娘科",
    "Nelumbonaceae": "莲科",
    "Nyctaginaceae": "紫茉莉科",
    "Nymphaeaceae": "睡莲科",
    "Oleaceae": "木犀科",
    "Onagraceae": "柳叶菜科",
    "Ophioglossaceae": "瓶尔小草科",
    "Orchidaceae": "兰科",
    "Oxalidaceae": "酢浆草科",
    "Paeoniaceae": "芍药科",
    "Pandanaceae": "露兜树科",
    "Papaveraceae": "罂粟科",
    "Paulowniaceae": "泡桐科",
    "Pentaphylacaceae": "五列木科",
    "Phrymaceae": "透骨草科",
    "Phyllanthaceae": "叶下珠科",
    "Phytolaccaceae": "商陆科",
    "Pinaceae": "松科",
    "Piperaceae": "胡椒科",
    "Pittosporaceae": "海桐科",
    "Plantaginaceae": "车前科",
    "Platanaceae": "悬铃木科",
    "Poaceae": "禾本科",
    "Podocarpaceae": "罗汉松科",
    "Polemoniaceae": "花荵科",
    "Polygonaceae": "蓼科",
    "Pontederiaceae": "雨久花科",
    "Portulacaceae": "马齿苋科",
    "Potamogetonaceae": "眼子菜科",
    "Primulaceae": "报春花科",
    "Ranunculaceae": "毛茛科",
    "Rhamnaceae": "鼠李科",
    "Rosaceae": "蔷薇科",
    "Rubiaceae": "茜草科",
    "Rutaceae": "芸香科",
    "Salicaceae": "杨柳科",
    "Sapindaceae": "无患子科",
    "Saururaceae": "三白草科",
    "Saxifragaceae": "虎耳草科",
    "Schisandraceae": "五味子科",
    "Scrophulariaceae": "玄参科",
    "Simaroubaceae": "苦木科",
    "Smilacaceae": "菝葜科",
    "Solanaceae": "茄科",
    "Stemonaceae": "百部科",
    "Strelitziaceae": "鹤望兰科",
    "Styracaceae": "安息香科",
    "Symplocaceae": "山矾科",
    "Tamaricaceae": "柽柳科",
    "Taxaceae": "红豆杉科",
    "Theaceae": "山茶科",
    "Thymelaeaceae": "瑞香科",
    "Tropaeolaceae": "旱金莲科",
    "Typhaceae": "香蒲科",
    "Ulmaceae": "榆科",
    "Urticaceae": "荨麻科",
    "Verbenaceae": "马鞭草科",
    "Violaceae": "堇菜科",
    "Xanthorrhoeaceae": "阿福花科",
    "Zamiaceae": "泽米铁科",
}


def safe_sheet_name(name: str, used: set[str]) -> str:
    for c in r"[]:*?/\\":
        name = name.replace(c, "_")
    name = str(name).strip()[:31]
    base = name
    i = 1
    while name in used:
        suf = f"_{i}"
        name = (base[: (31 - len(suf))] + suf)[:31]
        i += 1
    used.add(name)
    return name


def parse_binomial(scientific_name: str) -> str | None:
    """取学名前两词作为 GBIF 匹配用双名（忽略命名人）。"""
    s = str(scientific_name).strip()
    if not s:
        return None
    # 去括号变种等复杂情况：GBIF 仍可用前几词匹配
    tokens = re.split(r"\s+", s)
    if len(tokens) < 2:
        return None
    genus, epithet = tokens[0], tokens[1]
    if "'" in epithet or epithet.lower() == "x":
        return None
    # Cultivar 标记等
    epithet = re.sub(r"^[^\w.-]+|[^\w.-]+$", "", epithet)
    if not epithet:
        return None
    return f"{genus} {epithet}"


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")


def http_json(url: str) -> dict | list | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def gbif_chinese_or_translate(binomial: str, translator, cache: dict) -> str:
    key = binomial.strip()
    if key in cache:
        return cache[key]

    q = urllib.parse.quote(key)
    match = http_json(f"https://api.gbif.org/v1/species/match?name={q}&kingdom=Plantae&strict=false")
    if not isinstance(match, dict):
        cache[key] = ""
        return ""
    usage_key = match.get("usageKey")
    if not usage_key:
        cache[key] = ""
        return ""

    offset = 0
    zh_name = ""
    eng_name = ""
    while True:
        data = http_json(
            f"https://api.gbif.org/v1/species/{usage_key}/vernacularNames?limit=100&offset={offset}"
        )
        if not isinstance(data, dict):
            break
        for row in data.get("results") or []:
            lang = (row.get("language") or "").lower()
            vn = (row.get("vernacularName") or "").strip()
            if not vn:
                continue
            if lang in ("zho", "cmn", "zh"):
                zh_name = vn
                break
            if lang == "eng" and not eng_name:
                eng_name = vn
        if zh_name:
            break
        if data.get("endOfRecords"):
            break
        offset += 100

    if zh_name:
        cache[key] = zh_name
        return zh_name

    if eng_name and translator is not None:
        try:
            zh = translator.translate(eng_name)
            cache[key] = zh or ""
            time.sleep(0.15)
            return cache[key]
        except Exception:
            pass

    cache[key] = ""
    return ""


def scientific_raw_to_zh_map(raw_names: list[str], bio_cache: dict) -> dict[str, str]:
    """根据双名缓存，为每条原始学名（与表内字符串一致）生成中文名。"""
    m: dict[str, str] = {}
    for raw in raw_names:
        rs = str(raw).strip()
        if rs.lower() in ("nan", "none"):
            m[rs] = ""
            continue
        bio = parse_binomial(rs)
        if bio and bio in bio_cache:
            m[rs] = bio_cache[bio] or ""
        else:
            m[rs] = ""
    return m


def write_output_workbook(zh_map: dict[str, str] | None) -> None:
    """写入 Plants_Shanghai_Translated.xlsx（全部区 Sheet）。

    先完整写到同目录临时 .xlsx，再用 os.replace 原子覆盖目标文件，
    避免写入过程中 Excel 读到半成品导致「无法打开 / 文件已损坏」。
    """
    xl = pd.ExcelFile(SRC)
    used: set[str] = set()
    fd, tmp_name = tempfile.mkstemp(prefix="~Plants_Translated_", suffix=".xlsx", dir=str(BASE))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
            for sheet in xl.sheet_names:
                df = pd.read_excel(SRC, sheet_name=sheet)
                bilingual = add_bilingual_columns(df, zh_map)
                bilingual.to_excel(writer, sheet_name=safe_sheet_name(sheet, used), index=False)
        try:
            tmp_path.replace(OUT)
        except OSError as e:
            # 目标正被 Excel/云盘占用时，整本另存为，避免用户一直打不开
            if getattr(e, "winerror", None) in (5, 32) or e.errno in (13, 5, 11):
                alt = OUT.with_name(OUT.stem + "_recover.xlsx")
                if tmp_path.exists():
                    shutil.copy2(tmp_path, alt)
                tmp_path.unlink(missing_ok=True)
                print(
                    f"注意：{OUT.name} 正被占用，已完整写入 {alt.name}，"
                    f"请关闭正在打开的旧表后自行覆盖或改名。",
                    flush=True,
                )
            else:
                raise
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def enrich_names_stream(
    uniq: list[str],
    cache: dict,
    stream_every: int,
) -> dict[str, str]:
    """流式：边请求 GBIF / 翻译边落盘缓存；查到一种即重写整表（同名多行会一起填上）。

    stream_every:
      1（默认）：每处理完一个唯一学名就保存缓存并重写 xlsx。
      >1：每 N 个、或本次刚联网查到新结果时，重写。
      0：仅在「刚联网请求过」时重写（适合缓存已齐、不想反复写盘时）。
    """
    translator = GoogleTranslator(source="auto", target="zh-CN") if GoogleTranslator else None
    total = len(uniq)
    for i, raw in enumerate(uniq, start=1):
        bio = parse_binomial(str(raw).strip())
        fetched = False
        if bio and bio not in cache:
            gbif_chinese_or_translate(bio, translator, cache)
            fetched = True
            time.sleep(0.1)

        if stream_every == 1:
            do_write = True
        elif stream_every == 0:
            do_write = fetched
        else:
            do_write = fetched or (i % stream_every == 0)

        if do_write:
            save_cache(cache)
            zm = scientific_raw_to_zh_map(uniq, cache)
            write_output_workbook(zm)
            filled = sum(1 for v in zm.values() if str(v).strip())
            # 查到即提示；否则默认每 25 步报一次进度，避免刷屏
            if fetched or i == total or (stream_every == 1 and i % 25 == 0) or (
                stream_every > 1 and i % stream_every == 0
            ):
                print(
                    f"[stream] {i}/{total} → 已写入 {OUT.name}（有中文名 {filled}/{total} 种）",
                    flush=True,
                )

    save_cache(cache)
    return scientific_raw_to_zh_map(uniq, cache)


def zh_series_from_lookup(df: pd.DataFrame, zh_lookup: dict[str, str]) -> pd.Series:
    return (
        df["ScientificName"]
        .astype(str)
        .map(lambda x: zh_lookup.get(x, ""))
        .fillna("")
    )


def add_bilingual_columns(df: pd.DataFrame, zh_lookup: dict[str, str] | None) -> pd.DataFrame:
    zh_series = (
        zh_series_from_lookup(df, zh_lookup)
        if zh_lookup is not None
        else pd.Series([""] * len(df), index=df.index, dtype=object)
    )
    return pd.DataFrame(
        {
            "LocationID": df["LocationID"],
            "Locality": df["Locality"],
            "地点": df["Locality"].map(LOCALITY_ZH).fillna(""),
            "District": df["District"],
            "区": df["District"].map(DISTRICT_ZH).fillna(""),
            "Longitude": df["Longitude"],
            "Latitude": df["Latitude"],
            "ScientificName": df["ScientificName"],
            "中文名": zh_series,
            "Family": df["Family"],
            "科中文名": df["Family"].map(FAMILY_ZH).fillna(""),
            "Genus": df["Genus"],
            "属中文名": "",
            "SpecificEpithet": df["SpecificEpithet"],
            "种加词": df["SpecificEpithet"].astype(str),
            "TaxonRank": df["TaxonRank"],
            "分类阶元": df["TaxonRank"].map(TAXON_RANK_ZH).fillna(""),
            "GrowthForm": df["GrowthForm"],
            "生长型": df["GrowthForm"].map(GROWTH_ZH).fillna(""),
            "Plant_NativenessStatus": df["Plant_NativenessStatus"],
            "乡土性": df["Plant_NativenessStatus"].map(NATIVE_ZH).fillna(""),
            "SourceID": df["SourceID"],
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 Plants_Shanghai_Translated.xlsx")
    parser.add_argument(
        "--enrich-names",
        action="store_true",
        help="联网查询 GBIF 中文俗名（若无则英译中），较慢；默认可先空着「中文名」列",
    )
    parser.add_argument(
        "--stream-every",
        type=int,
        default=1,
        metavar="N",
        help="流式写盘：1=每处理 1 个学名就重写 xlsx（默认）；>1=每 N 个或联网新查到也写；0=仅联网新查到才写",
    )
    args = parser.parse_args()

    if not SRC.exists():
        raise SystemExit(f"缺少源文件: {SRC}")

    xl = pd.ExcelFile(SRC)
    name_cache = load_cache()

    if args.enrich_names:
        full = pd.concat(
            [pd.read_excel(SRC, sheet_name=s) for s in xl.sheet_names],
            ignore_index=True,
        )
        uniq = sorted(full["ScientificName"].astype(str).unique())
        # 先输出一版「仅有缓存命中」的表，便于立即打开文件
        write_output_workbook(scientific_raw_to_zh_map(uniq, name_cache))
        print(f"[init] 已根据缓存写出基准表 → {OUT}", flush=True)

        zh_map = enrich_names_stream(uniq, name_cache, args.stream_every)
        write_output_workbook(zh_map)
        print(f"完成：{OUT}（中文名已尽量填充，空单元可再运行本命令续跑）", flush=True)
    else:
        write_output_workbook(None)
        print("Wrote", OUT)


if __name__ == "__main__":
    main()
