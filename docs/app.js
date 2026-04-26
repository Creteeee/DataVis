const fmtPct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);
const fmtNum = (n) => (n == null ? "—" : new Intl.NumberFormat("en-US").format(n));
let onViewChanged = null;

function familyWikiUrl(name) {
  const n = (name ?? "").toString().trim();
  if (!n) return null;
  return `https://en.wikipedia.org/wiki/${encodeURIComponent(n)}`;
}

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return await res.json();
}

function setActiveChips(view) {
  document.querySelectorAll(".chip").forEach((b) => {
    b.classList.toggle("isActive", b.dataset.view === view);
  });
  document.getElementById("view-rq1").classList.toggle("isHidden", view !== "rq1");
  document.getElementById("view-rq2").classList.toggle("isHidden", view !== "rq2");
  document.getElementById("view-families").classList.toggle("isHidden", view !== "families");
  requestAnimationFrame(() => {
    if (typeof onViewChanged === "function") onViewChanged(view);
  });
}

function quantizeColor(ratio) {
  if (ratio == null) return "#64748b";
  // green -> amber
  const t = Math.max(0, Math.min(1, ratio));
  const a = { r: 22, g: 122, b: 74 };
  const b = { r: 181, g: 97, b: 18 };
  const mix = (x, y) => Math.round(x + (y - x) * t);
  return `rgb(${mix(a.r, b.r)}, ${mix(a.g, b.g)}, ${mix(a.b, b.b)})`;
}

function computeOverlapStats(overlap) {
  const vals = overlap.items.map((x) => x.jaccard).filter((x) => x != null);
  const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  const sorted = [...vals].sort((a, b) => a - b);
  const q = (p) => {
    if (!sorted.length) return null;
    const i = Math.floor((sorted.length - 1) * p);
    return sorted[i];
  };
  return { avg, p25: q(0.25), p50: q(0.5), p75: q(0.75) };
}

function normalizeDistrictName(name) {
  const raw = (name ?? "").toString().trim();
  const alias = {
    "Minhang District": "闵行",
    "Yangpu District": "杨浦",
    "Fengxian District": "奉贤",
    "Baoshan District": "宝山",
    "Pudong New Area": "浦东",
    "Xuhui District": "徐汇",
    "Songjiang District": "松江",
    "Jiading District": "嘉定",
    "Changning District": "长宁",
    "Jing'an District": "静安",
    "Hongkou District": "虹口",
    "Huangpu District": "黄浦",
    "Qingpu District": "青浦",
    "Jinshan District": "金山",
    "Putuo District": "普陀",
    "Chongming District": "崇明",
    "Chongming County": "崇明",
  };
  if (alias[raw]) return alias[raw];
  if (/^[\u4e00-\u9fa5]{2,4}$/.test(raw)) return raw;
  return raw.replace(/\s*District$/i, "").replace(/\s*New Area$/i, "").trim();
}

function buildDistrictCampusComparisonData(campusSummary, citySummary) {
  const cityRows = citySummary.districts
    .filter((d) => d.nonnativeRatio != null)
    .map((d) => ({
      districtRaw: d.district,
      districtNorm: normalizeDistrictName(d.district),
      districtRatio: d.nonnativeRatio,
    }));

  const byDistrict = new Map();
  for (const c of campusSummary.campuses) {
    if (c.nonnativeRatio == null) continue;
    const key = normalizeDistrictName(c.district);
    if (!byDistrict.has(key)) byDistrict.set(key, []);
    byDistrict.get(key).push(c);
  }

  const rows = cityRows.map((d) => {
    const campuses = byDistrict.get(d.districtNorm) || [];
    const campusAvg =
      campuses.length > 0
        ? campuses.reduce((acc, c) => acc + (c.nonnativeRatio ?? 0), 0) / campuses.length
        : null;
    return {
      districtRaw: d.districtRaw,
      districtNorm: d.districtNorm,
      districtRatio: d.districtRatio,
      hasCampus: campuses.length > 0,
      campusAvg,
      campuses: campuses.map((c) => ({ name: c.locality, ratio: c.nonnativeRatio })),
    };
  });

  rows.sort((a, b) => {
    if (a.hasCampus !== b.hasCampus) return a.hasCampus ? -1 : 1;
    return (b.districtRatio ?? -1) - (a.districtRatio ?? -1);
  });

  return rows;
}

function buildDistrictCampusComparisonDataFromRq2(campusItems, districtItems) {
  const districtMap = new Map(
    districtItems
      .filter((d) => d.nonnativeRatio != null)
      .map((d) => [d.district, d]),
  );
  const campusByDistrict = new Map();
  for (const c of campusItems) {
    if (c.nonnativeRatio == null) continue;
    const arr = campusByDistrict.get(c.district) || [];
    arr.push(c);
    campusByDistrict.set(c.district, arr);
  }

  const rows = [];
  for (const [district, d] of districtMap.entries()) {
    const campuses = campusByDistrict.get(district) || [];
    const campusAvg =
      campuses.length > 0
        ? campuses.reduce((s, c) => s + c.nonnativeRatio, 0) / campuses.length
        : null;
    rows.push({
      districtRaw: district,
      districtNorm: district,
      districtRatio: d.nonnativeRatio,
      hasCampus: campuses.length > 0,
      campusAvg,
      campuses: campuses.map((c) => ({ name: c.locality, ratio: c.nonnativeRatio })),
    });
  }

  rows.sort((a, b) => {
    if (a.hasCampus !== b.hasCampus) return a.hasCampus ? -1 : 1;
    return (b.districtRatio ?? -1) - (a.districtRatio ?? -1);
  });
  return rows;
}

function buildOverviewChart(el, campusSummary, citySummary, overlapStats) {
  const chart = echarts.init(el, null, { renderer: "canvas" });

  const campus = campusSummary.kpi;
  const city = citySummary.kpi;
  const percentSpecies = city.speciesCount ? campus.speciesCount / city.speciesCount : null;
  const percentGenus = city.genusCount ? campus.genusCount / city.genusCount : null;
  const percentFamilies = city.familyCount ? campus.familyCount / city.familyCount : null;

  const option = {
    grid: { left: 10, right: 14, top: 8, bottom: 22, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (v) => fmtNum(v),
    },
    xAxis: {
      type: "category",
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "rgba(20,30,35,0.18)" } },
      axisLabel: { color: "rgba(16,20,23,0.70)" },
      data: ["Species (unique)", "Genus (unique)", "Families (unique)"],
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(20,30,35,0.08)" } },
      axisLabel: { color: "rgba(16,20,23,0.70)" },
    },
    legend: {
      left: 0,
      textStyle: { color: "rgba(16,20,23,0.70)" },
      itemWidth: 10,
      itemHeight: 10,
    },
    series: [
      {
        name: "Campus (7 sites)",
        type: "bar",
        barMaxWidth: 34,
        itemStyle: { color: "rgba(11,106,103,0.72)", borderRadius: [8, 8, 0, 0] },
        data: [campus.speciesCount, campus.genusCount, campus.familyCount],
      },
      {
        name: "Shanghai (districts)",
        type: "bar",
        barMaxWidth: 34,
        itemStyle: { color: "rgba(16,20,23,0.18)", borderRadius: [8, 8, 0, 0] },
        data: [city.speciesCount, city.genusCount, city.familyCount],
      },
    ],
    graphic: [
      {
        type: "group",
        left: "58%",
        top: "6%",
        children: [
          {
            type: "text",
            style: {
              text: `Coverage (campus / city)`,
              fill: "rgba(16,20,23,0.55)",
              font: "600 11px ui-sans-serif, system-ui",
            },
          },
          {
            type: "text",
            top: 18,
            style: {
              text: `Species: ${percentSpecies == null ? "—" : (percentSpecies * 100).toFixed(1) + "%"}`,
              fill: "#101417",
              font: "700 12px ui-sans-serif, system-ui",
            },
          },
          {
            type: "text",
            top: 36,
            style: {
              text: `Genus: ${percentGenus == null ? "—" : (percentGenus * 100).toFixed(1) + "%"}`,
              fill: "#101417",
              font: "700 12px ui-sans-serif, system-ui",
            },
          },
          {
            type: "text",
            top: 54,
            style: {
              text: `Families: ${percentFamilies == null ? "—" : (percentFamilies * 100).toFixed(1) + "%"}`,
              fill: "#101417",
              font: "700 12px ui-sans-serif, system-ui",
            },
          },
          {
            type: "text",
            top: 72,
            style: {
              text: `Avg Jaccard (default Family): ${overlapStats.avg == null ? "—" : overlapStats.avg.toFixed(2)}`,
              fill: "rgba(16,20,23,0.70)",
              font: "600 11px ui-sans-serif, system-ui",
            },
          },
        ],
      },
    ],
  };

  chart.setOption(option);
  window.addEventListener("resize", () => chart.resize());
  return chart;
}

function buildCampusVsDistrictChart(el, campusSummary, citySummary, overlap, selectedCampus, metricLabel) {
  const chart = echarts.init(el, null, { renderer: "canvas" });

  const campus = campusSummary.campuses.find((c) => c.locality === selectedCampus);
  const distName = campus?.district;
  const dist = citySummary.districts.find((d) => d.district === distName);

  const data = [
    { metric: "Species", campus: campus?.speciesCount ?? null, district: dist?.speciesCount ?? null },
    { metric: "Genus", campus: campus?.genusCount ?? null, district: dist?.genusCount ?? null },
    { metric: "Family", campus: campus?.familyCount ?? null, district: dist?.familyCount ?? null },
  ];

  const ov = overlap.items.find((x) => x.campus === selectedCampus);

  chart.setOption({
    grid: { left: 10, right: 10, top: 8, bottom: 22, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "category",
      data: data.map((d) => d.metric),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "rgba(20,30,35,0.18)" } },
      axisLabel: { color: "rgba(16,20,23,0.70)" },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(20,30,35,0.08)" } },
      axisLabel: { color: "rgba(16,20,23,0.70)" },
    },
    legend: { left: 0, textStyle: { color: "rgba(16,20,23,0.70)" } },
    series: [
      {
        name: "Campus",
        type: "bar",
        itemStyle: { color: "rgba(11,106,103,0.72)", borderRadius: [8, 8, 0, 0] },
        data: data.map((d) => d.campus),
      },
      {
        name: "District",
        type: "bar",
        itemStyle: { color: "rgba(16,20,23,0.18)", borderRadius: [8, 8, 0, 0] },
        data: data.map((d) => d.district),
      },
    ],
    graphic: [
      {
        type: "text",
        right: 4,
        top: 4,
        style: {
          text: ov?.jaccard == null ? "Jaccard: —" : `Jaccard: ${ov.jaccard.toFixed(2)}`,
          fill: "rgba(16,20,23,0.70)",
          font: "600 11px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        },
      },
      {
        type: "text",
        right: 4,
        top: 22,
        style: {
          text:
            ov == null
              ? ""
              : `Shared ${metricLabel}: ${ov.sharedCount} / ${ov.unionCount}`,
          fill: "rgba(16,20,23,0.55)",
          font: "500 11px ui-sans-serif, system-ui",
        },
      },
    ],
  });

  window.addEventListener("resize", () => chart.resize());
  return chart;
}

function buildOverlapDistributionChart(el, overlap) {
  const chart = echarts.init(el, null, { renderer: "canvas" });
  const items = [...overlap.items]
    .filter((x) => x.jaccard != null)
    .sort((a, b) => (a.jaccard ?? 0) - (b.jaccard ?? 0));

  chart.setOption({
    grid: { left: 10, right: 10, top: 8, bottom: 22, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params) => {
        const p = params?.[0];
        if (!p) return "";
        const d = items[p.dataIndex];
        return `<div style="font-weight:700;margin-bottom:6px">${d.campus}</div>
          <div style="color:rgba(16,20,23,0.70)">District: ${d.district}</div>
          <div style="color:rgba(16,20,23,0.70)">Jaccard: ${d.jaccard.toFixed(2)}</div>`;
      },
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      splitLine: { lineStyle: { color: "rgba(20,30,35,0.08)" } },
      axisLabel: { color: "rgba(16,20,23,0.70)" },
    },
    yAxis: {
      type: "category",
      data: items.map((d) => d.campus),
      axisLabel: { color: "rgba(16,20,23,0.70)", width: 190, overflow: "truncate" },
      axisLine: { lineStyle: { color: "rgba(20,30,35,0.12)" } },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: items.map((d) => d.jaccard),
        barMaxWidth: 16,
        itemStyle: {
          borderRadius: 999,
          color: (p) => {
            const v = items[p.dataIndex].jaccard ?? 0;
            return `rgba(11,106,103,${0.20 + v * 0.65})`;
          },
        },
      },
    ],
  });
  window.addEventListener("resize", () => chart.resize());
  return chart;
}

function overlapMetricLabel(metric) {
  if (metric === "species") return "Species";
  if (metric === "genus") return "Genus";
  return "Family";
}

function buildSankey(el, sankey) {
  const chart = echarts.init(el, null, { renderer: "canvas" });
  const familyNames = new Set(
    (sankey.nodes || [])
      .filter((n) => n.kind === "family")
      .map((n) => n.name),
  );
  chart.setOption({
    tooltip: { trigger: "item", triggerOn: "mousemove" },
    series: [
      {
        type: "sankey",
        data: sankey.nodes.map((n) => ({
          name: n.name,
          kind: n.kind,
          itemStyle:
            n.kind === "district"
              ? { color: "rgba(11,106,103,0.55)" }
              : n.kind === "campus"
                ? { color: "rgba(16,20,23,0.22)" }
                : { color: "rgba(16,20,23,0.10)" },
        })),
        links: sankey.links,
        emphasis: { focus: "adjacency" },
        lineStyle: { color: "source", opacity: 0.25, curveness: 0.55 },
        nodeGap: 10,
        nodeWidth: 14,
        label: { color: "rgba(16,20,23,0.75)", fontSize: 11 },
      },
    ],
  });
  chart.off("click");
  chart.on("click", (params) => {
    if (params?.dataType !== "node") return;
    const nodeName = params?.name || params?.data?.name;
    if (!nodeName || !familyNames.has(nodeName)) return;
    const url = familyWikiUrl(nodeName);
    if (url) window.open(url, "_blank", "noopener,noreferrer");
  });
  window.addEventListener("resize", () => chart.resize());
  return chart;
}

function buildTreemap(el, treemap, mode) {
  const chart = echarts.init(el, null, { renderer: "canvas" });
  const root = mode === "city" ? treemap.city : treemap.campus;
  chart.setOption({
    tooltip: {
      formatter: (info) =>
        `<div style="font-weight:700;margin-bottom:6px">${info.name}</div>
         <div style="color:rgba(16,20,23,0.70)">Count: ${fmtNum(info.value)}</div>`,
    },
    series: [
      {
        type: "treemap",
        data: root.children,
        roam: false,
        breadcrumb: { show: false },
        label: { show: true, formatter: "{b}", color: "rgba(16,20,23,0.78)", fontSize: 11 },
        upperLabel: { show: false },
        itemStyle: { borderColor: "rgba(246,247,247,1)", borderWidth: 2, gapWidth: 2 },
        levels: [
          {
            itemStyle: {
              borderColor: "rgba(246,247,247,1)",
              borderWidth: 2,
              gapWidth: 2,
            },
          },
        ],
        color: [
          "rgba(11,106,103,0.80)",
          "rgba(11,106,103,0.58)",
          "rgba(11,106,103,0.40)",
          "rgba(16,20,23,0.18)",
        ],
      },
    ],
  });
  chart.off("click");
  chart.on("click", (params) => {
    const name = params?.name;
    if (!name) return;
    const url = familyWikiUrl(name);
    if (url) window.open(url, "_blank", "noopener,noreferrer");
  });
  window.addEventListener("resize", () => chart.resize());
  return chart;
}

function buildNonnativeDistribution(el, items, labelKey) {
  const chart = echarts.init(el, null, { renderer: "canvas" });
  const rows = [...items]
    .map((d) => ({ name: d[labelKey], v: d.nonnativeRatio }))
    .filter((d) => d.v != null)
    .sort((a, b) => (b.v ?? 0) - (a.v ?? 0));

  chart.setOption({
    grid: { left: 10, right: 10, top: 8, bottom: 22, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params) => {
        const p = params?.[0];
        if (!p) return "";
        const d = rows[p.dataIndex];
        return `<div style="font-weight:700;margin-bottom:6px">${d.name}</div>
          <div style="color:rgba(16,20,23,0.70)">Non-native: ${(d.v * 100).toFixed(1)}%</div>`;
      },
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      axisLabel: { formatter: (v) => `${Math.round(v * 100)}%`, color: "rgba(16,20,23,0.70)" },
      splitLine: { lineStyle: { color: "rgba(20,30,35,0.08)" } },
    },
    yAxis: {
      type: "category",
      data: rows.map((d) => d.name),
      axisLabel: { color: "rgba(16,20,23,0.70)", width: 200, overflow: "truncate" },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "rgba(20,30,35,0.12)" } },
    },
    series: [
      {
        type: "bar",
        data: rows.map((d) => d.v),
        barMaxWidth: 16,
        itemStyle: {
          borderRadius: 999,
          color: (p) => quantizeColor(rows[p.dataIndex].v),
        },
      },
    ],
  });
  window.addEventListener("resize", () => chart.resize());
  return { chart, rows };
}

function buildDistrictCampusCompareChart(el, rows) {
  const chart = echarts.init(el, null, { renderer: "canvas" });
  const labels = rows.map((r) => (r.hasCampus ? `${r.districtNorm} *` : r.districtNorm));
  chart.setOption({
    grid: { left: 10, right: 14, top: 20, bottom: 26, containLabel: true },
    legend: {
      left: 0,
      top: 0,
      textStyle: { color: "rgba(16,20,23,0.72)" },
      itemWidth: 10,
      itemHeight: 10,
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params) => {
        const p = params?.[0];
        if (!p) return "";
        const r = rows[p.dataIndex];
        const schools =
          r.campuses.length > 0
            ? r.campuses
                .map((x) => `${x.name}: ${(x.ratio * 100).toFixed(1)}%`)
                .join("<br/>")
            : "无学校样点";
        return `<div style="font-weight:800;margin-bottom:6px">${r.districtNorm}</div>
          <div style="color:rgba(16,20,23,0.75)">区非乡土: ${(r.districtRatio * 100).toFixed(1)}%</div>
          <div style="color:rgba(16,20,23,0.75)">校园均值: ${r.campusAvg == null ? "—" : (r.campusAvg * 100).toFixed(1) + "%"}</div>
          <div style="margin-top:6px;color:rgba(16,20,23,0.65)">${schools}</div>`;
      },
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      axisLabel: { formatter: (v) => `${Math.round(v * 100)}%`, color: "rgba(16,20,23,0.70)" },
      splitLine: { lineStyle: { color: "rgba(20,30,35,0.08)" } },
    },
    yAxis: {
      type: "category",
      data: labels,
      axisLabel: { color: "rgba(16,20,23,0.70)" },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "rgba(20,30,35,0.12)" } },
    },
    series: [
      {
        name: "行政区",
        type: "bar",
        data: rows.map((r) => r.districtRatio),
        barMaxWidth: 14,
        itemStyle: { color: "rgba(16,20,23,0.28)", borderRadius: 999 },
      },
      {
        name: "校园（所在区均值）",
        type: "bar",
        data: rows.map((r) => r.campusAvg),
        barMaxWidth: 14,
        itemStyle: { color: "rgba(11,106,103,0.82)", borderRadius: 999 },
      },
    ],
  });
  window.addEventListener("resize", () => chart.resize());
  return chart;
}

function formatExtremaRows(items, nameKey, valueKey = "v") {
  const valid = items.filter((x) => x[valueKey] != null);
  if (!valid.length) {
    return { min: "—", max: "—", avg: "—" };
  }
  const min = valid.reduce((a, b) => (a[valueKey] <= b[valueKey] ? a : b));
  const max = valid.reduce((a, b) => (a[valueKey] >= b[valueKey] ? a : b));
  const avg = valid.reduce((s, x) => s + x[valueKey], 0) / valid.length;
  return {
    min: `${(min[valueKey] * 100).toFixed(1)}% (${min[nameKey]})`,
    max: `${(max[valueKey] * 100).toFixed(1)}% (${max[nameKey]})`,
    avg: `${(avg * 100).toFixed(1)}%`,
  };
}

function renderRq2StatsTable(tableEl, campusRows, districtRows) {
  const campusStats = formatExtremaRows(campusRows, "name", "v");
  const districtStats = formatExtremaRows(districtRows, "districtNorm", "districtRatio");
  const body = tableEl.querySelector("tbody");
  body.innerHTML = `
    <tr>
      <td>学校（校区）</td>
      <td>${campusStats.min}</td>
      <td>${campusStats.max}</td>
      <td>${campusStats.avg}</td>
    </tr>
    <tr>
      <td>行政区</td>
      <td>${districtStats.min}</td>
      <td>${districtStats.max}</td>
      <td>${districtStats.avg}</td>
    </tr>
  `;
}

function buildMap(el, campuses) {
  const map = L.map(el, {
    zoomControl: true,
    scrollWheelZoom: true,
  }).setView([31.23, 121.47], 10);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const maxSpecies = Math.max(...campuses.map((c) => c.speciesCount));
  const nativeRatios = campuses
    .map((c) => (c.nonnativeRatio == null ? null : 1 - c.nonnativeRatio))
    .filter((v) => v != null)
    .sort((a, b) => a - b);
  const nativeMedian =
    nativeRatios.length === 0
      ? null
      : nativeRatios.length % 2 === 1
        ? nativeRatios[(nativeRatios.length - 1) / 2]
        : (nativeRatios[nativeRatios.length / 2 - 1] + nativeRatios[nativeRatios.length / 2]) / 2;

  campuses.forEach((c) => {
    if (c.latitude == null || c.longitude == null) return;
    const r = 10 + (c.speciesCount / maxSpecies) * 22;
    const nativeRatio = c.nonnativeRatio == null ? null : 1 - c.nonnativeRatio;
    const isHighNative = nativeMedian == null || nativeRatio == null ? false : nativeRatio >= nativeMedian;
    const color = isHighNative ? "rgba(22,122,74,0.90)" : "rgba(181,97,18,0.92)";
    const circle = L.circleMarker([c.latitude, c.longitude], {
      radius: r * 0.70,
      color,
      weight: 2,
      fillColor: color,
      fillOpacity: isHighNative ? 0.35 : 0.26,
    }).addTo(map);

    const html = `
      <div style="font-weight:800;margin-bottom:6px">${c.locality}</div>
      <div style="color:rgba(16,20,23,0.75)">District: ${c.district}</div>
      <div style="color:rgba(16,20,23,0.75)">Species: ${fmtNum(c.speciesCount)} · Families: ${fmtNum(c.familyCount)}</div>
      <div style="color:rgba(16,20,23,0.75)">Native: ${fmtPct(nativeRatio)} · Non-native: ${fmtPct(c.nonnativeRatio)}</div>
      <div style="color:rgba(16,20,23,0.75)">Class: ${nativeMedian == null ? "—" : isHighNative ? "High Native" : "Low Native"} (median=${fmtPct(nativeMedian)})</div>
    `;
    circle.bindPopup(html, { maxWidth: 320 });
  });

  return map;
}

async function main() {
  const [campusSummary, citySummary, overlapTaxa, rq2Taxa, sankey, treemap] = await Promise.all([
    loadJson("./data/campus_summary.json"),
    loadJson("./data/city_district_summary.json"),
    loadJson("./data/overlap_taxa.json"),
    loadJson("./data/rq2_taxa_native_nonnative.json"),
    loadJson("./data/sankey_district_campus_family.json"),
    loadJson("./data/treemap_families.json"),
  ]);

  let activeMetric = "family";
  let overlap = overlapTaxa[activeMetric];
  const overlapStats = computeOverlapStats(overlap);

  document.getElementById("kpiCampusSpecies").textContent = fmtNum(campusSummary.kpi.speciesCount);
  document.getElementById("kpiCitySpecies").textContent = fmtNum(citySummary.kpi.speciesCount);
  document.getElementById("kpiFamilyOverlap").textContent =
    overlapStats.avg == null ? "—" : overlapStats.avg.toFixed(2);
  document.getElementById("kpiOverlapLabel").textContent =
    `校园-所在区 ${overlapMetricLabel(activeMetric)} 重叠（均值）`;
  document.getElementById("asOfMeta").textContent = `campus=${campusSummary.kpi.campusCount} · city_districts=${citySummary.kpi.districtCount}`;

  // View switching
  setActiveChips("rq1");
  document.querySelectorAll(".chip").forEach((b) => {
    b.addEventListener("click", () => setActiveChips(b.dataset.view));
  });

  // Overview
  const overviewChart = buildOverviewChart(
    document.getElementById("chartOverview"),
    campusSummary,
    citySummary,
    overlapStats,
  );

  // Campus select + charts
  const sel = document.getElementById("campusSelect");
  const metricSel = document.getElementById("overlapMetricSelect");
  campusSummary.campuses.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.locality;
    opt.textContent = c.locality;
    sel.appendChild(opt);
  });
  sel.value = campusSummary.campuses[0]?.locality ?? "";

  let campusVsDistrictChart = null;
  let overlapChart = buildOverlapDistributionChart(document.getElementById("chartOverlap"), overlap);
  const renderCampus = () => {
    campusVsDistrictChart?.dispose?.();
    campusVsDistrictChart = buildCampusVsDistrictChart(
      document.getElementById("chartCampusVsDistrict"),
      campusSummary,
      citySummary,
      overlap,
      sel.value,
      overlapMetricLabel(activeMetric),
    );
  };
  renderCampus();
  sel.addEventListener("change", renderCampus);
  metricSel.addEventListener("change", () => {
    activeMetric = metricSel.value;
    overlap = overlapTaxa[activeMetric];
    overlapChart.dispose();
    overlapChart = buildOverlapDistributionChart(document.getElementById("chartOverlap"), overlap);
    const newStats = computeOverlapStats(overlap);
    document.getElementById("kpiFamilyOverlap").textContent =
      newStats.avg == null ? "—" : newStats.avg.toFixed(2);
    document.getElementById("kpiOverlapLabel").textContent =
      `校园-所在区 ${overlapMetricLabel(activeMetric)} 重叠（均值）`;
    renderCampus();
  });

  // Sankey
  const sankeyChart = buildSankey(document.getElementById("chartSankey"), sankey);

  // Map
  const map = buildMap(document.getElementById("map"), campusSummary.campuses);

  // RQ2: non-native comparisons
  const rq2MetricSel = document.getElementById("rq2MetricSelect");
  let rq2Metric = rq2MetricSel?.value || "family";
  let cityN = null;
  let campusN = null;
  let districtCampusChart = null;
  const rq2MetricName = (m) => (m === "species" ? "Species" : m === "genus" ? "Genus" : "Family");

  const renderRQ2 = () => {
    const level = rq2Taxa[rq2Metric] || rq2Taxa.family;
    const districts = (level?.districts || []).filter((d) => d.district !== "Unknown");
    const campuses = level?.campuses || [];

    cityN?.chart?.dispose?.();
    campusN?.chart?.dispose?.();
    districtCampusChart?.dispose?.();

    cityN = buildNonnativeDistribution(
      document.getElementById("chartCityNonnative"),
      districts,
      "district",
    );
    campusN = buildNonnativeDistribution(
      document.getElementById("chartCampusNonnative"),
      campuses,
      "locality",
    );

    const topCity = cityN.rows[0];
    const topCampus = campusN.rows[0];
    const avgCity =
      cityN.rows.length ? cityN.rows.reduce((a, b) => a + (b.v ?? 0), 0) / cityN.rows.length : null;
    const avgCampus =
      campusN.rows.length
        ? campusN.rows.reduce((a, b) => a + (b.v ?? 0), 0) / campusN.rows.length
        : null;
    document.querySelector("#rq2Callout .calloutBody").innerHTML =
      `（${rq2MetricName(rq2Metric)}）上海全市（按区）非乡土比例均值：<strong>${avgCity == null ? "—" : (avgCity * 100).toFixed(1) + "%"}</strong>；` +
      `校园样点均值：<strong>${avgCampus == null ? "—" : (avgCampus * 100).toFixed(1) + "%"}</strong>。` +
      `<br/>最高的区：<strong>${topCity?.name ?? "—"}</strong>（${topCity?.v == null ? "—" : (topCity.v * 100).toFixed(1) + "%"}），` +
      `最高的校园：<strong>${topCampus?.name ?? "—"}</strong>（${topCampus?.v == null ? "—" : (topCampus.v * 100).toFixed(1) + "%"}）。`;

    const districtCampusRows = buildDistrictCampusComparisonDataFromRq2(campuses, districts);
    districtCampusChart = buildDistrictCampusCompareChart(
      document.getElementById("chartDistrictCampusCompare"),
      districtCampusRows,
    );
    renderRq2StatsTable(
      document.getElementById("rq2StatsTable"),
      campusN.rows,
      districtCampusRows,
    );

    document.getElementById("rq2CityTitle").textContent =
      `上海全市：非乡土比例分布（${rq2MetricName(rq2Metric)}）`;
    document.getElementById("rq2CampusTitle").textContent =
      `校园：非乡土比例分布（${rq2MetricName(rq2Metric)}）`;
    document.getElementById("rq2CompareTitle").textContent =
      `学校放入所在区后：区 vs 校园（双颜色对比，${rq2MetricName(rq2Metric)}）`;
  };

  renderRQ2();
  rq2MetricSel?.addEventListener("change", () => {
    rq2Metric = rq2MetricSel.value;
    renderRQ2();
  });

  // Treemap toggle
  let treemapMode = "campus";
  let treemapChart = buildTreemap(document.getElementById("chartTreemap"), treemap, treemapMode);
  document.querySelectorAll(".segBtn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".segBtn").forEach((b) => b.classList.remove("isActive"));
      btn.classList.add("isActive");
      treemapMode = btn.dataset.treemap;
      treemapChart.dispose();
      treemapChart = buildTreemap(document.getElementById("chartTreemap"), treemap, treemapMode);
    });
  });

  // Fix: charts created under hidden tabs need explicit resize after tab switch.
  onViewChanged = () => {
    overviewChart?.resize?.();
    campusVsDistrictChart?.resize?.();
    overlapChart?.resize?.();
    sankeyChart?.resize?.();
    cityN?.chart?.resize?.();
    campusN?.chart?.resize?.();
    districtCampusChart?.resize?.();
    treemapChart?.resize?.();
    map?.invalidateSize?.();
  };
}

main().catch((err) => {
  console.error(err);
  const pre = document.createElement("pre");
  pre.style.whiteSpace = "pre-wrap";
  pre.style.padding = "16px";
  pre.style.border = "1px solid rgba(20,30,35,0.16)";
  pre.style.borderRadius = "12px";
  pre.style.background = "#fff";
  pre.textContent = String(err?.stack || err);
  document.body.prepend(pre);
});

