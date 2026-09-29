import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { geoEquirectangular, geoGraticule10, geoPath } from "d3-geo";
import Papa from "papaparse";
import { feature } from "topojson-client";
import type { Feature, Geometry } from "geojson";
import type { Topology, Objects } from "topojson-specification";
import countries from "world-atlas/countries-110m.json";
import { ExternalLink, Filter, Maximize2, Minus, Plus, Wind } from "lucide-react";
import { Badge, Inline, Table, Text } from "@studio-baeks/paper-ui";

type TrackPoint = { sid: string; season: number; basin: string; name: string; time: string; lat: number; lon: number; wind: number | null; pressure: number | null; status: string };
type Storm = { sid: string; season: number; name: string; basin: string; points: TrackPoint[]; peakWind: number; minPressure: number | null; start: string; end: string };
type CountryTopology = Topology<Objects<{ name: string }>>;
type ChartSeries = { name: string; color: string; values: (number | null)[] };
type ClimateRow = { year: number; month: number; gridId: number; lat: number; lon: number; temperature: number; humidity: number; temperatureAnomaly: number; humidityAnomaly: number };
type ClimateNormal = { month: number; gridId: number; lat: number; lon: number; temperature: number; humidity: number };
type AirMassRow = { month: number; gridId: number; lat: number; lon: number; temperature850: number; humidity850: number; height500: number; u850: number; v850: number };

function ZoomableSvg({ className, ariaLabel, children }: { className: string; ariaLabel: string; children: ReactNode }) {
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ pointerId: number; clientX: number; clientY: number; x: number; y: number; moved: boolean } | null>(null);
  const draggedRef = useRef(false);
  const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
  const clampView = (next: { scale: number; x: number; y: number }) => ({ scale: next.scale, x: clamp(next.x, 820 * (1 - next.scale), 0), y: clamp(next.y, 460 * (1 - next.scale), 0) });
  const zoomAt = (scale: number, x: number, y: number) => setView((current) => {
    const nextScale = clamp(scale, 1, 8);
    return clampView({ scale: nextScale, x: x - (x - current.x) * nextScale / current.scale, y: y - (y - current.y) * nextScale / current.scale });
  });
  const zoomBy = (factor: number) => zoomAt(view.scale * factor, 410, 230);

  return <div className="zoomable-map">
    <div className="map-zoom-controls" role="group" aria-label="지도 확대 및 이동">
      <button type="button" aria-label="지도 확대" title="확대" onClick={() => zoomBy(1.35)}><Plus size={15} /></button>
      <button type="button" aria-label="지도 축소" title="축소" onClick={() => zoomBy(1 / 1.35)}><Minus size={15} /></button>
      <button type="button" aria-label="지도 초기화" title="초기화" onClick={() => setView({ scale: 1, x: 0, y: 0 })}><Maximize2 size={14} /></button>
    </div>
    <svg ref={svgRef} className={className} viewBox="0 0 820 460" role="img" aria-label={ariaLabel} tabIndex={0}
      onKeyDown={(event) => {
        if (!event.metaKey && !event.ctrlKey) return;
        if (event.key === "+" || event.key === "=" || event.code === "NumpadAdd") { event.preventDefault(); event.stopPropagation(); zoomBy(1.35); }
        else if (event.key === "-" || event.key === "_" || event.code === "NumpadSubtract") { event.preventDefault(); event.stopPropagation(); zoomBy(1 / 1.35); }
        else if (event.key === "0" || event.code === "Numpad0") { event.preventDefault(); event.stopPropagation(); setView({ scale: 1, x: 0, y: 0 }); }
      }}
      onPointerDown={(event) => { if (event.button !== 0) return; event.currentTarget.setPointerCapture(event.pointerId); dragRef.current = { pointerId: event.pointerId, clientX: event.clientX, clientY: event.clientY, x: view.x, y: view.y, moved: false }; }}
      onPointerMove={(event) => { const drag = dragRef.current; if (!drag || drag.pointerId !== event.pointerId) return; const bounds = event.currentTarget.getBoundingClientRect(); const dx = (event.clientX - drag.clientX) / bounds.width * 820; const dy = (event.clientY - drag.clientY) / bounds.height * 460; if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true; if (drag.moved) setView((current) => clampView({ ...current, x: drag.x + dx, y: drag.y + dy })); }}
      onPointerUp={(event) => { const drag = dragRef.current; if (drag?.pointerId === event.pointerId) { draggedRef.current = drag.moved; dragRef.current = null; } }}
      onPointerCancel={() => { dragRef.current = null; }}
      onClickCapture={(event) => { if (draggedRef.current) { event.preventDefault(); event.stopPropagation(); draggedRef.current = false; } }}>
      <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>{children}</g>
    </svg>
    <span className="map-zoom-hint">지도 포커스 후 ⌘/Ctrl + / − · 드래그 이동</span>
  </div>;
}

function LineChart({ years, series, label, unit, height = 126 }: { years: number[]; series: ChartSeries[]; label: string; unit: string; height?: number }) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(300);
  useEffect(() => {
    const element = chartRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setChartWidth(Math.max(300, entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const values = series.flatMap((item) => item.values.filter((value): value is number => value !== null));
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const range = max - min || 1;
  const plotLeft = 48;
  const plotRight = chartWidth - 8;
  const x = (index: number) => plotLeft + (years.length <= 1 ? 0 : index / (years.length - 1) * (plotRight - plotLeft));
  const y = (value: number) => height - 18 - ((value - min) / range) * (height - 34);
  return <div className="line-chart-wrap" ref={chartRef}>
    <svg className="line-chart" viewBox={`0 0 ${chartWidth} ${height}`} role="img" aria-label={label}>
      {[0, 0.5, 1].map((fraction) => { const value = min + range * fraction; const py = y(value); return <g key={fraction}><line x1={plotLeft} x2={plotRight} y1={py} y2={py} className="chart-gridline" /><text x={plotLeft - 6} y={py - 3} textAnchor="end" className="chart-tick">{Math.round(value * 10) / 10}</text></g>; })}
      {series.map((item) => {
        const coords = item.values.map((value, index) => value === null ? null : `${x(index)},${y(value)}`).filter(Boolean);
        return <g key={item.name}><polyline points={coords.join(" ")} fill="none" stroke={item.color} strokeWidth="1.25" strokeLinejoin="round" strokeLinecap="round" />{item.values.map((value, index) => value === null ? null : <circle key={years[index]} cx={x(index)} cy={y(value)} r="1.35" fill={item.color}><title>{years[index]} · {item.name}: {value.toFixed(1)} {unit}</title></circle>)}</g>;
      })}
      <text x={plotLeft} y={height - 3} className="chart-tick">{years[0] ?? "—"}</text><text x={plotRight} y={height - 3} textAnchor="end" className="chart-tick">{years.at(-1) ?? "—"}</text>
    </svg>
    <div className="series-legend">{series.map((item) => <span key={item.name}><i style={{ background: item.color }} />{item.name}</span>)}</div>
  </div>;
}

const topo = countries as unknown as CountryTopology;
const land = feature(topo, topo.objects.countries) as Feature<Geometry>;
const projection = geoEquirectangular().center([0, 0]).scale(130).translate([410, 230]);
const path = geoPath(projection);
const gridPath = path(geoGraticule10());
const LAND_PATH = path(land) ?? "";
const DATA_SOURCE = "https://www.ncei.noaa.gov/products/international-best-track-archive";
const CLIMATE_SOURCE = "https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html";
const HUMIDITY_SOURCE = "https://www.metoffice.gov.uk/hadobs/hadisdh/";
const PUI = { ink: "var(--pui-color-ink-primary)", info: "var(--pui-color-accent-info-solid)", success: "var(--pui-color-accent-success-solid)", warning: "var(--pui-color-accent-warning-solid)", error: "var(--pui-color-accent-error-solid)" };
const BASIN_LABELS: Record<string, string> = { NA: "북대서양", EP: "동태평양", WP: "북서태평양", NI: "북인도양", SI: "남인도양", SP: "남태평양", SA: "남대서양", MM: "지중해" };

function parseNumber(value: string | undefined): number | null {
  if (!value?.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeLongitude(longitude: number): number {
  return ((longitude + 180) % 360 + 360) % 360 - 180;
}

function windClass(wind: number): string {
  if (wind >= 96) return "severe";
  if (wind >= 64) return "strong";
  if (wind >= 34) return "storm";
  return "depression";
}

function formatWind(knots: number): string {
  return `${Math.round(knots)} kt`;
}

export function App() {
  const [points, setPoints] = useState<TrackPoint[]>([]);
  const [loadError, setLoadError] = useState("");
  const [basin, setBasin] = useState("ALL");
  const [season, setSeason] = useState("2025");
  const [selectedId, setSelectedId] = useState("");
  const [query, setQuery] = useState("");
  const [windThreshold, setWindThreshold] = useState(64);
  const [climateRows, setClimateRows] = useState<ClimateRow[]>([]);
  const [climateNormals, setClimateNormals] = useState<ClimateNormal[]>([]);
  const [airMassRows, setAirMassRows] = useState<AirMassRow[]>([]);
  const [climateError, setClimateError] = useState("");
  const [climateYear, setClimateYear] = useState("2024");
  const [climateMonth, setClimateMonth] = useState(8);
  const [climateMetric, setClimateMetric] = useState<"temperature" | "humidity" | "airmass" | "upperair">("temperature");

  useEffect(() => {
      Papa.parse<Record<string, string>>("/data/ibtracs_global_since1980.csv", {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        const parsed = result.data.filter((row) => row.SID && row.SID.trim()).map((row) => ({
          sid: row.SID.trim(), season: Number(row.SEASON), basin: row.BASIN.trim(), name: row.NAME.trim(),
          time: row.ISO_TIME.trim(), lat: Number(row.LAT), lon: Number(row.LON), wind: parseNumber(row.WMO_WIND),
          pressure: parseNumber(row.WMO_PRES), status: row.NATURE.trim(),
        })).filter((point) => Number.isFinite(point.season) && Number.isFinite(point.lat) && Number.isFinite(point.lon));
        setPoints(parsed);
        if (result.errors.length) setLoadError("일부 행을 읽지 못했습니다. 화면에 읽힌 자료만 표시합니다.");
      },
      error: () => setLoadError("자료 파일을 불러오지 못했습니다."),
    });
  }, []);

  useEffect(() => {
    Papa.parse<Record<string, string>>("/data/hadisdh_global_monthly.csv", {
      download: true, header: true, skipEmptyLines: true,
      complete: (result) => setClimateRows(result.data.map((row) => ({ year: Number(row.year), month: Number(row.month), gridId: Number(row.grid_id), lat: Number(row.lat), lon: Number(row.lon), temperature: Number(row.temperature_c), humidity: Number(row.relative_humidity_pct), temperatureAnomaly: Number(row.temperature_anomaly_c), humidityAnomaly: Number(row.humidity_anomaly_pct) })).filter((row) => Number.isFinite(row.year) && Number.isFinite(row.temperature) && Number.isFinite(row.humidity))),
      error: () => setClimateError("기후 자료 파일을 불러오지 못했습니다."),
    });
    Papa.parse<Record<string, string>>("/data/hadisdh_global_normals.csv", {
      download: true, header: true, skipEmptyLines: true,
      complete: (result) => setClimateNormals(result.data.map((row) => ({ month: Number(row.month), gridId: Number(row.grid_id), lat: Number(row.lat), lon: Number(row.lon), temperature: Number(row.temperature_c), humidity: Number(row.relative_humidity_pct) })).filter((row) => Number.isFinite(row.month) && Number.isFinite(row.temperature))),
      error: () => setClimateError("평년값 자료 파일을 불러오지 못했습니다."),
    });
    Papa.parse<Record<string, string>>("/data/ncep_global_airmass_normals.csv", {
      download: true, header: true, skipEmptyLines: true,
      complete: (result) => setAirMassRows(result.data.map((row) => ({ month: Number(row.month), gridId: Number(row.grid_id), lat: Number(row.lat), lon: Number(row.lon), temperature850: Number(row.temperature_850_c), humidity850: Number(row.relative_humidity_850_pct), height500: Number(row.geopotential_height_500_m), u850: Number(row.u_wind_850_ms), v850: Number(row.v_wind_850_ms) })).filter((row) => Number.isFinite(row.month) && Number.isFinite(row.temperature850))),
      error: () => setClimateError("상층 대기 자료 파일을 불러오지 못했습니다."),
    });
  }, []);

  const storms = useMemo(() => {
    const grouped = new Map<string, TrackPoint[]>();
    for (const point of points) {
      if (basin !== "ALL" && point.basin !== basin) continue;
      const list = grouped.get(point.sid) ?? [];
      list.push(point);
      grouped.set(point.sid, list);
    }
    return [...grouped.entries()].map(([sid, track]) => {
      track.sort((a, b) => a.time.localeCompare(b.time));
      const winds = track.flatMap((point) => point.wind === null ? [] : [point.wind]);
      const pressures = track.flatMap((point) => point.pressure === null ? [] : [point.pressure]);
      const first = track[0];
      return { sid, season: first.season, name: first.name || "이름 없음", basin: first.basin, points: track,
        peakWind: winds.length ? Math.max(...winds) : 0, minPressure: pressures.length ? Math.min(...pressures) : null,
        start: first.time.slice(0, 10), end: track[track.length - 1].time.slice(0, 10) } satisfies Storm;
    }).sort((a, b) => b.season - a.season || b.peakWind - a.peakWind);
  }, [points, basin]);

  const seasons = useMemo(() => [...new Set(storms.map((storm) => storm.season))].sort((a, b) => b - a), [storms]);
  const visibleStorms = useMemo(() => storms.filter((storm) => (season === "ALL" || storm.season === Number(season)) && storm.name.toLowerCase().includes(query.toLowerCase())), [storms, season, query]);
  const activeStorm = visibleStorms.find((storm) => storm.sid === selectedId) ?? visibleStorms[0];
  const mapStorms = season === "ALL" ? visibleStorms : visibleStorms;
  const pointsInSeason = mapStorms.reduce((sum, storm) => sum + storm.points.length, 0);
  const peak = mapStorms.reduce((max, storm) => Math.max(max, storm.peakWind), 0);
  const yearly = useMemo(() => [...seasons].sort((a, b) => a - b).map((year) => ({ year, count: storms.filter((storm) => storm.season === year).length })), [storms, seasons]);
  const maxCount = Math.max(1, ...yearly.map((item) => item.count));
  const analytics = useMemo(() => {
    const years = yearly.map(({ year }) => year);
    const windByYear = years.map((year) => {
      const values = storms.filter((storm) => storm.season === year && storm.peakWind > 0).map((storm) => storm.peakWind);
      return { year, mean: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null, max: values.length ? Math.max(...values) : null,
        threshold: storms.filter((storm) => storm.season === year && storm.peakWind >= windThreshold).length };
    });
    const centers = new Map<string, { lat: number; lon: number }>();
    for (const storm of storms) {
      const byBasin = new Map<string, TrackPoint[]>();
      for (const point of storm.points) { const list = byBasin.get(point.basin) ?? []; list.push(point); byBasin.set(point.basin, list); }
      for (const [stormBasin, track] of byBasin) {
        const key = `${storm.season}-${stormBasin}`; const center = centers.get(key) ?? { lat: 0, lon: 0 };
        center.lat += track.reduce((sum, point) => sum + point.lat, 0) / track.length;
        center.lon += track.reduce((sum, point) => sum + point.lon, 0) / track.length;
        const countKey = `${key}-count`; const previous = centers.get(countKey) ?? { lat: 0, lon: 0 }; previous.lat += 1; centers.set(countKey, previous); centers.set(key, center);
      }
    }
    const trackSeries = (field: "lat" | "lon", basinName: string, color: string): ChartSeries => ({ name: basinName, color, values: years.map((year) => { const key = `${year}-${basinName}`; const count = centers.get(`${key}-count`)?.lat ?? 0; return count ? (centers.get(key)?.[field] ?? 0) / count : null; }) });
    return { years, windByYear, latitude: [trackSeries("lat", "WP", PUI.info), trackSeries("lat", "NI", PUI.warning)], longitude: [trackSeries("lon", "WP", PUI.info), trackSeries("lon", "NI", PUI.warning)] };
  }, [storms, yearly, windThreshold]);
  const climate = useMemo(() => {
    const normal = new Map(climateNormals.filter((row) => row.month === climateMonth).map((row) => [row.gridId, row]));
    const current = climateYear === "NORMAL" ? [] : climateRows.filter((row) => row.year === Number(climateYear) && row.month === climateMonth);
    const displayRows = climateYear === "NORMAL"
      ? climateNormals.filter((row) => row.month === climateMonth).map((row) => ({ gridId: row.gridId, lat: row.lat, lon: row.lon, temperature: row.temperature, humidity: row.humidity, normalTemperature: row.temperature, normalHumidity: row.humidity, temperatureAnomaly: 0, humidityAnomaly: 0 }))
      : current.map((row) => { const ref = normal.get(row.gridId); return { gridId: row.gridId, lat: row.lat, lon: row.lon, temperature: row.temperature, humidity: row.humidity, normalTemperature: ref?.temperature ?? row.temperature, normalHumidity: ref?.humidity ?? row.humidity, temperatureAnomaly: row.temperatureAnomaly, humidityAnomaly: row.humidityAnomaly }; });
    const yearlyClimate = [...new Set(climateRows.map((row) => row.year))].sort((a, b) => a - b).map((year) => {
      const rows = climateRows.filter((row) => row.year === year);
      const monthly = Array.from({ length: 12 }, (_, month) => rows.filter((row) => row.month === month + 1));
      const mean = (monthRows: ClimateRow[], field: "temperatureAnomaly" | "humidityAnomaly") => {
        if (!monthRows.length) return null;
        const weighted = monthRows.reduce((sum, row) => sum + row[field] * Math.cos(row.lat * Math.PI / 180), 0);
        return weighted / monthRows.reduce((sum, row) => sum + Math.cos(row.lat * Math.PI / 180), 0);
      };
      const tValues = monthly.map((monthRows) => mean(monthRows, "temperatureAnomaly")).filter((value): value is number => value !== null);
      const rhValues = monthly.map((monthRows) => mean(monthRows, "humidityAnomaly")).filter((value): value is number => value !== null);
      return { year, temperatureAnomaly: tValues.length ? tValues.reduce((sum, value) => sum + value, 0) / tValues.length : null, humidityAnomaly: rhValues.length ? rhValues.reduce((sum, value) => sum + value, 0) / rhValues.length : null };
    });
    return { displayRows, yearlyClimate, airMass: airMassRows.filter((row) => row.month === climateMonth) };
  }, [climateRows, climateNormals, airMassRows, climateMonth, climateYear]);
  const climateMapRows = climateMetric === "upperair"
    ? climate.airMass.map((row) => ({ gridId: row.gridId, lat: row.lat, lon: row.lon, temperature: row.temperature850, humidity: row.humidity850, normalTemperature: row.temperature850, normalHumidity: row.humidity850, temperatureAnomaly: 0, humidityAnomaly: 0, h500: row.height500, u850: row.u850, v850: row.v850 }))
    : climate.displayRows.map((row) => ({ ...row, h500: null as number | null, u850: null as number | null, v850: null as number | null }));
  const yFor = (lat: number) => projection([0, lat])?.[1] ?? 0;
  const xFor = (lon: number) => projection([normalizeLongitude(lon), 0])?.[0] ?? 0;

  return (
    <main className="atlas-shell">
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark"><Wind size={16} /></span> Cyclone Atlas</a>
          <div className="topbar-right"><span className="source-dot" /> NOAA IBTrACS v04r01 <span className="topbar-divider" /> Global · 1980–2026</div>
      </header>

      <div className="page" id="top">
        <section className="intro-row">
          <div>
            <Text variant="title" as="h1">전 세계 열대저기압 아틀라스</Text>
            <Text variant="body" className="intro-copy">1980년 이후 전 세계에서 관측된 열대저기압의 경로·강도와 기후 조건을 살펴봅니다.</Text>
          </div>
          <a className="source-link" href={DATA_SOURCE} target="_blank" rel="noreferrer">데이터 출처 <ExternalLink size={14} /></a>
        </section>

        <section className="controlbar" aria-label="자료 필터">
          <div className="filter-label"><Filter size={15} /><Text variant="label">범위</Text></div>
          <div className="segment-control basin-control" role="group" aria-label="해역 선택">{["ALL", ...new Set(points.map((point) => point.basin))].map((code) => <button key={code} className={basin === code ? "active" : ""} onClick={() => setBasin(code)}>{code === "ALL" ? "전 세계" : `${BASIN_LABELS[code] ?? "기타 해역"} (${code})`}</button>)}</div>
          <label className="select-wrap"><span>연도</span><select value={season} onChange={(event) => { setSeason(event.target.value); setSelectedId(""); }}><option value="ALL">전체 연도</option>{seasons.map((year) => <option key={year} value={year}>{year}</option>)}</select></label>
          <label className="search-wrap"><span className="sr-only">태풍 이름 검색</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="태풍 이름 검색" /></label>
        </section>

        {loadError && <div className="load-warning" role="status">{loadError}</div>}
        {!points.length && !loadError && <div className="loading"><span className="spinner" /> NOAA 태풍 경로 자료를 불러오는 중입니다…</div>}

        <section className="metrics" aria-label="선택 범위 요약">
          <div className="metric"><span>열대저기압 수</span><strong>{storms.length ? visibleStorms.length.toLocaleString() : "—"}</strong><small>{season === "ALL" ? "1980년 이후" : `${season}년`} · 고유 SID 기준</small></div>
          <div className="metric"><span>경로 관측점</span><strong>{points.length ? pointsInSeason.toLocaleString() : "—"}</strong><small>대체로 3–6시간 간격</small></div>
          <div className="metric"><span>최대 풍속</span><strong>{peak ? formatWind(peak) : "—"}</strong><small>WMO 기준 · 최대 지속풍</small></div>
          <div className="metric metric-note"><span>해역 범위</span><strong>{basin === "ALL" ? "전 세계" : basin}</strong><small>{basin === "ALL" ? "IBTrACS 전체 해역 코드" : "IBTrACS 해역 코드 기준"}</small></div>
        </section>

        <section className="visual-grid">
          <article className="panel map-panel">
            <div className="panel-heading"><div><Text variant="heading" as="h2">태풍 경로</Text><Text variant="caption">{season === "ALL" ? "전체 연도 경로를 겹쳐 표시" : `${season}년 경로 · 태풍을 선택하면 강조됩니다`}</Text></div><div className="map-legend"><i className="legend-line" /> 경로 <i className="legend-dot" /> 중심 위치</div></div>
            <div className="map-wrap">
              <ZoomableSvg className="map" ariaLabel="전 세계 열대저기압 경로 지도">
                <rect width="820" height="460" className="ocean" />
                <path d={gridPath ?? ""} className="graticule" />
                <path d={LAND_PATH} className="land" />
                {mapStorms.map((storm) => {
                  const route = storm.points.filter((point) => point.lat > -80 && point.lat < 80);
                  const selected = storm.sid === activeStorm?.sid;
                  if (route.length < 2) return null;
                  const d = route.map((point, index) => `${index && Math.abs(normalizeLongitude(point.lon) - normalizeLongitude(route[index - 1].lon)) < 180 ? "L" : "M"}${xFor(point.lon).toFixed(1)},${yFor(point.lat).toFixed(1)}`).join(" ");
                  const last = route[route.length - 1];
                  return <g key={storm.sid} className={`track ${windClass(storm.peakWind)} ${selected ? "selected" : ""}`} onClick={() => setSelectedId(storm.sid)}>
                    <title>{storm.name} · {storm.season} · peak {formatWind(storm.peakWind)}</title><path d={d} className="track-line" /><circle cx={xFor(last.lon)} cy={yFor(last.lat)} r={selected ? 4.5 : 2.2} className="track-point" />
                  </g>;
                })}
              </ZoomableSvg>
              <div className="map-lat-label lat-top">60°N</div><div className="map-lat-label lat-bottom">60°S</div>
              {!visibleStorms.length && points.length > 0 && <div className="map-empty">조건에 맞는 태풍이 없습니다.</div>}
            </div>
            <div className="map-footer"><span><b>{visibleStorms.length.toLocaleString()}</b>개 태풍 경로</span><span>색상은 최대 풍속 구간을 나타냅니다</span></div>
          </article>

          <aside className="side-column">
            <article className="panel trend-panel">
              <div className="panel-heading"><div><Text variant="heading" as="h2">연도별 발생 수</Text><Text variant="caption">전 세계 또는 선택 해역 · 고유 SID 기준</Text></div><span className="trend-period">1980—26</span></div>
              <div className="chart" role="img" aria-label="연도별 태풍 발생 수 막대 그래프">
                {yearly.map(({ year, count }) => <button key={year} className={`bar-wrap ${season === String(year) ? "chosen" : ""} ${year === yearly[yearly.length - 1]?.year ? "current-year" : ""}`} title={`${year}: ${count}개${year === 2026 ? " · 진행 중" : ""}`} onClick={() => setSeason(String(year))}>
                  <span className="bar-value">{count}</span><span className="bar" style={{ height: `${Math.max(3, count / maxCount * 100)}%` }} /><span className="bar-year">{year % 10 === 0 || year === yearly[yearly.length - 1]?.year ? String(year).slice(-2) : ""}</span>
                </button>)}
              </div>
              <div className="chart-axis"><span>{yearly[0]?.year ?? "—"}</span><span>연도 · 2026 진행 중</span><span>{yearly[yearly.length - 1]?.year ?? "—"}</span></div>
            </article>
            <article className="panel selected-panel">
              <div className="panel-heading"><div><Text variant="heading" as="h2">선택한 태풍</Text><Text variant="caption">지도 또는 목록에서 선택</Text></div></div>
              {activeStorm ? <div className="storm-detail">
                <Inline justify="between" align="center"><div><div className="storm-name">{activeStorm.name}</div><div className="storm-meta">{activeStorm.season} · {activeStorm.basin} · {activeStorm.points.length}개 위치</div></div><Badge color="warning" variant="soft">{activeStorm.basin}</Badge></Inline>
              <div className="storm-facts"><div><span>최대 풍속</span><b>{activeStorm.peakWind > 0 ? formatWind(activeStorm.peakWind) : "—"}</b></div><div><span>최저 기압</span><b>{activeStorm.minPressure ? `${activeStorm.minPressure} hPa` : "—"}</b></div></div>
                <div className="storm-dates"><span>{activeStorm.start}</span><span className="date-rule" /><span>{activeStorm.end}</span></div>
              </div> : <div className="empty-detail">표시할 태풍이 없습니다.</div>}
            </article>
          </aside>
        </section>

        <section className="analytics-section" aria-label="태풍 경향 분석">
          <div className="analytics-heading"><div><Text variant="heading" as="h2">태풍 강도와 경로 경향</Text><Text variant="caption">연도별 · 선택한 해역 기준 · 열대저기압별 최대 풍속을 사용</Text></div></div>
          <div className="analytics-grid">
            <article className="panel analytics-card"><div className="panel-heading"><div><Text variant="heading" as="h3">평균·최대 풍속</Text><Text variant="caption">태풍별 WMO 최대 풍속의 연간 평균과 최댓값</Text></div></div>
              <LineChart years={analytics.years} label="연도별 태풍 최대 풍속 평균과 최댓값" unit="kt" series={[{ name: "평균", color: PUI.info, values: analytics.windByYear.map((item) => item.mean) }, { name: "최대", color: PUI.error, values: analytics.windByYear.map((item) => item.max) }]} />
            </article>
            <article className="panel analytics-card"><div className="panel-heading"><div><Text variant="heading" as="h3">강한 태풍 빈도</Text><Text variant="caption">태풍별 최대 풍속이 기준 이상인 연간 개수</Text></div></div>
              <div className="threshold-control" role="group" aria-label="풍속 기준 선택">{[34, 64, 96].map((threshold) => <button key={threshold} className={windThreshold === threshold ? "active" : ""} onClick={() => setWindThreshold(threshold)}>{threshold}+ kt</button>)}</div>
              <div className="threshold-chart">{analytics.windByYear.map((item) => { const max = Math.max(1, ...analytics.windByYear.map((row) => row.threshold)); return <div key={item.year} className="threshold-column" title={`${item.year}: ${item.threshold}개`}><i style={{ height: `${Math.max(2, item.threshold / max * 100)}%` }} /><span>{item.year % 10 === 0 || item.year === analytics.years.at(-1) ? String(item.year).slice(-2) : ""}</span></div>; })}</div>
              <div className="chart-axis"><span>{analytics.years[0] ?? "—"}</span><span>{windThreshold} kt 이상 · 태풍 수</span><span>{analytics.years.at(-1) ?? "—"}</span></div>
            </article>
            <article className="panel analytics-card track-analysis"><div className="panel-heading"><div><Text variant="heading" as="h3">태풍 경로 중심 이동</Text><Text variant="caption">해역별로 태풍마다 평균 좌표를 구한 뒤 연도 평균</Text></div></div>
              <div className="track-mini-grid"><div><span className="axis-title">위도 (°)</span><LineChart years={analytics.years} label="태풍별 평균 경로 중심 위도" unit="°" height={112} series={analytics.latitude} /></div><div><span className="axis-title">경도 (°)</span><LineChart years={analytics.years} label="태풍별 평균 경로 중심 경도" unit="°" height={112} series={analytics.longitude} /></div></div>
            </article>
          </div>
          <p className="analysis-note">풍속 기준은 IBTrACS WMO_WIND(knot)이며 기관별 지속시간 기준 차이는 보정하지 않았습니다. 2026년은 진행 중입니다. 경로 중심은 태풍별 관측 좌표 평균으로 계산하므로 이동거리나 경로 밀도와는 다른 지표입니다.</p>
        </section>

        <section className="climate-section" aria-label="전 세계 기온·습도와 기단 조건">
          <div className="climate-heading"><div><Text variant="heading" as="h2">전 세계 기후 평년값과 기단 조건</Text><Text variant="caption">Met Office HadISDH.blend · 1973–2024 · 10° 격자 · 1991–2020 평년</Text></div>
            <div className="climate-controls"><label>자료 시점<select value={climateYear} onChange={(event) => { setClimateYear(event.target.value); if (event.target.value === "NORMAL" && climateMetric === "airmass") setClimateMetric("temperature"); }}><option value="NORMAL">1991–2020 평년</option>{[...new Set(climateRows.map((row) => row.year))].sort((a, b) => b - a).map((year) => <option key={year} value={year}>{year}</option>)}</select></label><label>월<select value={climateMonth} onChange={(event) => setClimateMonth(Number(event.target.value))}>{Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}월</option>)}</select></label></div>
          </div>
          {climateError && <div className="load-warning">{climateError}</div>}
          {!climateRows.length && !climateError ? <div className="loading climate-loading"><span className="spinner" />기후 평년값·습도 자료를 불러오는 중입니다…</div> : <div className="climate-layout">
            <article className="panel climate-map-panel"><div className="panel-heading"><div><Text variant="heading" as="h3">{climateMetric === "temperature" ? "2m 평균 기온" : climateMetric === "humidity" ? "2m 상대습도" : climateMetric === "upperair" ? "850 hPa 기온 평년" : "기단 열·수분 편차"}</Text><Text variant="caption">{climateMetric === "upperair" ? "1991–2020 상층 대기 평년 · 850 hPa" : climateYear === "NORMAL" ? "1991–2020 월별 기후 평년" : `${climateYear}년 ${climateMonth}월 · 평년 대비`}</Text></div>
              <div className="metric-switch" role="group" aria-label="기후 지도 변수"><button className={climateMetric === "temperature" ? "active" : ""} onClick={() => setClimateMetric("temperature")}>기온</button><button className={climateMetric === "humidity" ? "active" : ""} onClick={() => setClimateMetric("humidity")}>습도</button><button disabled={climateYear === "NORMAL"} className={climateMetric === "airmass" ? "active" : ""} onClick={() => setClimateMetric("airmass")}>기단 조건</button><button className={climateMetric === "upperair" ? "active" : ""} onClick={() => setClimateMetric("upperair")}>상층장</button></div>
            </div>
              <div className="climate-map-wrap"><ZoomableSvg className="climate-map" ariaLabel="전 세계 월별 기온, 상대습도, 기단 조건 및 상층 대기 지도"><rect width="820" height="460" className="ocean"/><path d={gridPath ?? ""} className="graticule"/><path d={LAND_PATH} className="land"/>{climateMapRows.map((row) => {
                const anomalyT = row.temperatureAnomaly; const anomalyRh = row.humidityAnomaly;
                const fill = climateMetric === "airmass" ? anomalyT >= 0 ? (anomalyRh >= 0 ? PUI.success : PUI.warning) : (anomalyRh >= 0 ? PUI.info : PUI.ink) : climateMetric === "temperature" ? row.temperature < 0 ? PUI.info : row.temperature < 15 ? "var(--pui-color-ink-tertiary)" : row.temperature < 25 ? PUI.warning : PUI.error : climateMetric === "humidity" ? `color-mix(in srgb, var(--pui-color-accent-info-solid) ${Math.max(18, Math.min(100, row.humidity))}%, var(--pui-color-bg-raised))` : `color-mix(in srgb, var(--pui-color-accent-info-solid) ${Math.max(18, Math.min(100, (row.temperature + 35) * 1.5))}%, var(--pui-color-bg-raised))`;
                const latitudeLabel = `${Math.abs(row.lat)}°${row.lat < 0 ? "S" : "N"}`; const longitudeLabel = `${Math.abs(row.lon > 180 ? row.lon - 360 : row.lon)}°${row.lon > 180 || row.lon < 0 ? "W" : "E"}`;
                const extra = row.h500 !== null ? ` · RH850 ${row.humidity.toFixed(0)}% · Z500 ${row.h500.toFixed(0)} m · wind850 ${(Math.hypot(row.u850 ?? 0, row.v850 ?? 0)).toFixed(1)} m/s` : ` · ΔT ${anomalyT >= 0 ? "+" : ""}${anomalyT.toFixed(1)}°C · ΔRH ${anomalyRh >= 0 ? "+" : ""}${anomalyRh.toFixed(0)}%p`;
                return <circle key={row.gridId} cx={xFor(row.lon)} cy={yFor(row.lat)} r="3.3" fill={fill} stroke="var(--pui-color-bg-raised)" strokeWidth=".7"><title>{latitudeLabel}, {longitudeLabel} · {row.temperature.toFixed(1)}°C · RH {row.humidity.toFixed(0)}%{extra}</title></circle>;
              })}</ZoomableSvg></div>
              <div className="climate-legend">{climateMetric === "airmass" ? <><span><i style={{ background: PUI.success }} />온난·습윤</span><span><i style={{ background: PUI.warning }} />온난·건조</span><span><i style={{ background: PUI.info }} />한랭·습윤</span><span><i style={{ background: PUI.ink }} />한랭·건조</span></> : <><span><i className={`legend-gradient ${climateMetric === "humidity" ? "humidity-scale" : climateMetric === "upperair" ? "upperair-scale" : "temperature-scale"}`} />{climateMetric === "temperature" ? "저온 → 고온 (°C)" : climateMetric === "upperair" ? "850 hPa 기온 (°C)" : "저습 → 고습 (%)"}</span><span>{climateMetric === "upperair" ? climate.airMass.length : climate.displayRows.length}개 격자</span></>}</div>
            </article>
            <div className="climate-trends">
              <article className="panel analytics-card"><div className="panel-heading"><div><Text variant="heading" as="h3">전 지구 기온 편차</Text><Text variant="caption">1991–2020 월평년 대비 · 위도 면적 가중</Text></div></div><LineChart years={climate.yearlyClimate.map((row) => row.year)} label="전 세계 2미터 기온 연평균 편차" unit="°C" height={140} series={[{ name: "기온 편차", color: PUI.warning, values: climate.yearlyClimate.map((row) => row.temperatureAnomaly) }]} /></article>
              <article className="panel analytics-card"><div className="panel-heading"><div><Text variant="heading" as="h3">전 지구 상대습도 편차</Text><Text variant="caption">1991–2020 월평년 대비 · 위도 면적 가중</Text></div></div><LineChart years={climate.yearlyClimate.map((row) => row.year)} label="전 세계 상대습도 연평균 편차" unit="%p" height={140} series={[{ name: "RH 편차", color: PUI.info, values: climate.yearlyClimate.map((row) => row.humidityAnomaly) }]} /></article>
            </div>
          </div>}
          <p className="analysis-note">기온·습도는 HadISDH의 관측 기반 월 편차(1991–2020 평년)와 실제값을 함께 사용합니다. 관측이 없는 10° 격자는 보간하지 않아 지도에 빈칸으로 남습니다. 기단 조건 지도는 선택 연·월 편차 부호로 만든 탐색용 4분면(온난/한랭 × 습윤/건조)입니다. 상층장은 NCEP/NCAR의 850 hPa 기온·상대습도·바람과 500 hPa 지위고도 월평년입니다. 공기덩이의 발생지와 이동 경로를 추적한 공식 기단 분류는 아닙니다.</p>
        </section>

        <section className="panel table-panel">
          <div className="panel-heading table-title"><div><Text variant="heading" as="h2">열대저기압 목록</Text><Text variant="caption">이름, 기간, 관측된 최대 풍속 · 행을 누르면 경로가 강조됩니다</Text></div><span className="record-count">{visibleStorms.length.toLocaleString()}건</span></div>
          <div className="table-scroll"><Table variant="ruled">
            <colgroup><col style={{ width: "8%" }} /><col style={{ width: "22%" }} /><col style={{ width: "8%" }} /><col style={{ width: "25%" }} /><col style={{ width: "18%" }} /><col style={{ width: "19%" }} /></colgroup>
            <Table.Header sticky><Table.Column align="center">시즌</Table.Column><Table.Column>태풍</Table.Column><Table.Column align="center">해역</Table.Column><Table.Column>기간</Table.Column><Table.Column align="end">최대 풍속</Table.Column><Table.Column align="end">최저 기압</Table.Column></Table.Header>
            <Table.Body>{visibleStorms.slice(0, 100).map((storm) => <Table.Row key={storm.sid} className={storm.sid === activeStorm?.sid ? "table-selected" : "table-clickable"} onClick={() => setSelectedId(storm.sid)}>
              <Table.Cell align="center">{storm.season}</Table.Cell><Table.Cell><strong>{storm.name}</strong><span className="storm-id">{storm.sid}</span></Table.Cell><Table.Cell align="center">{storm.basin}</Table.Cell><Table.Cell>{storm.start} – {storm.end}</Table.Cell><Table.Cell numeric><span className={`wind-tag ${windClass(storm.peakWind)}`}>{storm.peakWind > 0 ? formatWind(storm.peakWind) : "—"}</span></Table.Cell><Table.Cell numeric>{storm.minPressure ? `${storm.minPressure} hPa` : "—"}</Table.Cell>
            </Table.Row>)}</Table.Body>
          </Table></div>
          {visibleStorms.length > 100 && <div className="table-more">목록에는 최신순 100개만 표시합니다. 연도나 해역 필터로 좁혀보세요.</div>}
        </section>

        <footer className="footer"><span>Storms: NOAA NCEI · IBTrACS v04r01</span><a href={DATA_SOURCE} target="_blank" rel="noreferrer">태풍 자료 설명 <ExternalLink size={12} /></a><span>Climate: Met Office · HadISDH.blend 1.5.1.2024f</span><a href={HUMIDITY_SOURCE} target="_blank" rel="noreferrer">기후 자료 설명 <ExternalLink size={12} /></a><span>Upper air: NOAA PSL · NCEP/NCAR Reanalysis 1</span><a href={CLIMATE_SOURCE} target="_blank" rel="noreferrer">상층 자료 설명 <ExternalLink size={12} /></a><span className="footnote">IBTrACS는 열대저압부 등도 포함합니다. 2026년 태풍 시즌은 진행 중이며 최근 자료는 수정될 수 있습니다. 풍속은 WMO_WIND(knot)이며 기관별 평균 시간 차이는 보정하지 않았습니다. HadISDH는 빈 관측 격자를 보간하지 않아 지도에 빈칸이 남습니다.</span></footer>
      </div>
    </main>
  );
}
