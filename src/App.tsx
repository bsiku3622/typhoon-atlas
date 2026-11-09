import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { geoEquirectangular, geoGraticule10, geoPath } from "d3-geo";
import Papa from "papaparse";
import { feature } from "topojson-client";
import type { Feature, Geometry } from "geojson";
import type { Topology, Objects } from "topojson-specification";
import countries from "world-atlas/countries-110m.json";
import { ExternalLink, Maximize2, Minus, Plus, Search } from "lucide-react";
import { Badge, Box, Divider, Field, Grid, IconButton, Inline, Label, Link, SegmentControl, Select, Spinner, Stack, Surface, Text } from "@studio-baeks/paper-ui";
import { tokens } from "@studio-baeks/paper-ui/tokens";
import { Metric, Panel, PanelHeading, SourceBadge, TopBar } from "./chrome";

type TrackPoint = { sid: string; season: number; basin: string; name: string; time: string; lat: number; lon: number; wind: number | null; pressure: number | null; status: string };
type Storm = { sid: string; season: number; name: string; basin: string; points: TrackPoint[]; peakWind: number; minPressure: number | null; start: string; end: string };
type CountryTopology = Topology<Objects<{ name: string }>>;
type ChartSeries = { name: string; color: string; values: (number | null)[] };
type ClimateRow = { year: number; month: number; gridId: number; lat: number; lon: number; temperature: number; humidity: number; temperatureAnomaly: number; humidityAnomaly: number };
type ClimateNormal = { month: number; gridId: number; lat: number; lon: number; temperature: number; humidity: number };
type AirMassRow = { month: number; gridId: number; lat: number; lon: number; temperature850: number; humidity850: number; height500: number; u850: number; v850: number };
type TemperatureStormPoint = { year: number; globalTemperature: number; tropicalTemperature: number; count: number; strongCount: number; meanPeakWind: number | null };

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
      <IconButton variant="hairline" size="xs" aria-label="지도 확대" title="확대" onClick={() => zoomBy(1.35)}><Plus /></IconButton>
      <IconButton variant="hairline" size="xs" aria-label="지도 축소" title="축소" onClick={() => zoomBy(1 / 1.35)}><Minus /></IconButton>
      <IconButton variant="hairline" size="xs" aria-label="지도 초기화" title="초기화" onClick={() => setView({ scale: 1, x: 0, y: 0 })}><Maximize2 /></IconButton>
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
    <Badge className="map-zoom-hint" variant="hairline" size="xs">지도 포커스 후 ⌘/Ctrl + / − · 드래그 이동</Badge>
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

function fitLine(points: { x: number; y: number }[]) {
  if (points.length < 2) return null;
  const meanX = points.reduce((sum, point) => sum + point.x, 0) / points.length;
  const meanY = points.reduce((sum, point) => sum + point.y, 0) / points.length;
  const covariance = points.reduce((sum, point) => sum + (point.x - meanX) * (point.y - meanY), 0);
  const varianceX = points.reduce((sum, point) => sum + (point.x - meanX) ** 2, 0);
  const varianceY = points.reduce((sum, point) => sum + (point.y - meanY) ** 2, 0);
  if (!varianceX || !varianceY) return null;
  const slope = covariance / varianceX;
  return { slope, intercept: meanY - slope * meanX, correlation: covariance / Math.sqrt(varianceX * varianceY) };
}

function TemperatureRelationshipChart({ rows, temperatureScope, metric, title, description, color }: {
  rows: TemperatureStormPoint[];
  temperatureScope: "globalTemperature" | "tropicalTemperature";
  metric: "count" | "strongCount" | "meanPeakWind";
  title: string;
  description: string;
  color: string;
}) {
  const validRows = rows.flatMap((row) => {
    const y = row[metric];
    return y === null ? [] : [{ year: row.year, x: row[temperatureScope], y }];
  });
  const regression = fitLine(validRows);
  const xValues = validRows.map((point) => point.x);
  const yValues = validRows.map((point) => point.y);
  const xMin = Math.min(...xValues, -0.1);
  const xMax = Math.max(...xValues, 0.1);
  const yMin = Math.min(...yValues, 0);
  const yMax = Math.max(...yValues, 1);
  const xPad = Math.max((xMax - xMin) * 0.08, 0.04);
  const yPad = Math.max((yMax - yMin) * 0.08, metric === "meanPeakWind" ? 1 : 0.5);
  const left = 48; const right = 338; const top = 14; const bottom = 160;
  const x = (value: number) => left + (value - (xMin - xPad)) / (xMax - xMin + 2 * xPad) * (right - left);
  const y = (value: number) => bottom - (value - (yMin - yPad)) / (yMax - yMin + 2 * yPad) * (bottom - top);
  const residualize = (key: "x" | "y") => {
    const yearFit = fitLine(validRows.map((point) => ({ x: point.year, y: point[key] })));
    return yearFit ? validRows.map((point) => ({ year: point.year, residual: point[key] - (yearFit.intercept + yearFit.slope * point.year) })) : [];
  };
  const xResiduals = residualize("x"); const yResiduals = residualize("y");
  const yResidualByYear = new Map(yResiduals.map((point) => [point.year, point.residual]));
  const detrended = fitLine(xResiduals.flatMap((point) => { const residual = yResidualByYear.get(point.year); return residual === undefined ? [] : [{ x: point.residual, y: residual }]; }));
  const decadeColor = (year: number) => year < 1990 ? PUI.info : year < 2000 ? PUI.success : year < 2010 ? PUI.warning : year < 2020 ? PUI.error : PUI.ink;
  const xTicks = [xMin, (xMin + xMax) / 2, xMax];
  const yTicks = [yMin, (yMin + yMax) / 2, yMax];
  return <Panel className="temperature-chart-card">
    <PanelHeading level="subheading" title={title} caption={description} />
    <Inline gap="md" wrap className="relationship-stats"><Text variant="label" ink="tertiary" numeric as="span">Pearson r <Text variant="label" strong as="b">{regression ? regression.correlation.toFixed(2) : "—"}</Text></Text><Text variant="label" ink="tertiary" numeric as="span">연도 추세 제거 r* <Text variant="label" strong as="b">{detrended ? detrended.correlation.toFixed(2) : "—"}</Text></Text><Text variant="label" ink="tertiary" numeric as="span">연도 <Text variant="label" strong as="b">{validRows.length}</Text></Text></Inline>
    <svg className="relationship-chart" viewBox="0 0 360 205" role="img" aria-label={`${title}: 기온 편차와 태풍 ${description}의 상관 그래프`}>
      {yTicks.map((tick, index) => <g key={index}><line x1={left} x2={right} y1={y(tick)} y2={y(tick)} className="chart-gridline" /><text x={left - 7} y={y(tick) + 3} textAnchor="end" className="chart-tick">{metric === "meanPeakWind" ? tick.toFixed(0) : tick.toFixed(0)}</text></g>)}
      {xTicks.map((tick, index) => <text key={index} x={x(tick)} y={bottom + 15} textAnchor={index === 0 ? "start" : index === xTicks.length - 1 ? "end" : "middle"} className="chart-tick">{tick.toFixed(1)}</text>)}
      {regression && <line x1={x(xMin - xPad)} y1={y(regression.intercept + regression.slope * (xMin - xPad))} x2={x(xMax + xPad)} y2={y(regression.intercept + regression.slope * (xMax + xPad))} stroke={color} strokeWidth="1.5" strokeDasharray="4 3" opacity=".75" />}
      {validRows.map((point) => <circle key={point.year} cx={x(point.x)} cy={y(point.y)} r="3.2" fill={decadeColor(point.year)} stroke={tokens.color.bg.raised} strokeWidth="1"><title>{`${point.year} · 기온 편차 ${point.x.toFixed(2)} °C · ${description} ${point.y.toFixed(metric === "meanPeakWind" ? 1 : 0)}`}</title></circle>)}
      <text x={(left + right) / 2} y="199" textAnchor="middle" className="scatter-axis-title">기온 편차 (°C)</text>
      <text transform={`translate(11 ${(top + bottom) / 2}) rotate(-90)`} textAnchor="middle" className="scatter-axis-title">{metric === "meanPeakWind" ? "평균 최대풍속 (kt)" : "태풍 수"}</text>
    </svg>
    <div className="decade-legend">{[["80년대", PUI.info], ["90년대", PUI.success], ["00년대", PUI.warning], ["10년대", PUI.error], ["20년대", PUI.ink]].map(([label, decadeColor]) => <span key={label as string}><i style={{ background: decadeColor as string }} />{label}</span>)}</div>
  </Panel>;
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
const PUI = { ink: tokens.color.ink.primary, info: tokens.color.accent.info.solid, success: tokens.color.accent.success.solid, warning: tokens.color.accent.warning.solid, error: tokens.color.accent.error.solid };
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
  const [temperatureScope, setTemperatureScope] = useState<"globalTemperature" | "tropicalTemperature">("tropicalTemperature");

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
      const mean = (monthRows: ClimateRow[], field: "temperatureAnomaly" | "humidityAnomaly", tropicalOnly = false) => {
        const selected = tropicalOnly ? monthRows.filter((row) => Math.abs(row.lat) <= 30) : monthRows;
        if (!selected.length) return null;
        const weighted = selected.reduce((sum, row) => sum + row[field] * Math.cos(row.lat * Math.PI / 180), 0);
        return weighted / selected.reduce((sum, row) => sum + Math.cos(row.lat * Math.PI / 180), 0);
      };
      const tValues = monthly.map((monthRows) => mean(monthRows, "temperatureAnomaly")).filter((value): value is number => value !== null);
      const tropicalTValues = monthly.map((monthRows) => mean(monthRows, "temperatureAnomaly", true)).filter((value): value is number => value !== null);
      const rhValues = monthly.map((monthRows) => mean(monthRows, "humidityAnomaly")).filter((value): value is number => value !== null);
      return { year, temperatureAnomaly: tValues.length ? tValues.reduce((sum, value) => sum + value, 0) / tValues.length : null, tropicalTemperatureAnomaly: tropicalTValues.length ? tropicalTValues.reduce((sum, value) => sum + value, 0) / tropicalTValues.length : null, humidityAnomaly: rhValues.length ? rhValues.reduce((sum, value) => sum + value, 0) / rhValues.length : null };
    });
    return { displayRows, yearlyClimate, airMass: airMassRows.filter((row) => row.month === climateMonth) };
  }, [climateRows, climateNormals, airMassRows, climateMonth, climateYear]);
  const climateMapRows = climateMetric === "upperair"
    ? climate.airMass.map((row) => ({ gridId: row.gridId, lat: row.lat, lon: row.lon, temperature: row.temperature850, humidity: row.humidity850, normalTemperature: row.temperature850, normalHumidity: row.humidity850, temperatureAnomaly: 0, humidityAnomaly: 0, h500: row.height500, u850: row.u850, v850: row.v850 }))
    : climate.displayRows.map((row) => ({ ...row, h500: null as number | null, u850: null as number | null, v850: null as number | null }));
  const temperatureStormRows = useMemo(() => {
    const temperatures = new Map(climate.yearlyClimate.map((row) => [row.year, row]));
    const stormsByYear = new Map<number, Storm[]>();
    for (const storm of storms) {
      if (storm.season < 1980 || storm.season > 2024) continue;
      const list = stormsByYear.get(storm.season) ?? [];
      list.push(storm); stormsByYear.set(storm.season, list);
    }
    return Array.from({ length: 45 }, (_, index) => 1980 + index).flatMap((year) => {
      const climateYearData = temperatures.get(year);
      if (!climateYearData || climateYearData.temperatureAnomaly === null || climateYearData.tropicalTemperatureAnomaly === null) return [];
      const annualStorms = stormsByYear.get(year) ?? [];
      const winds = annualStorms.map((storm) => storm.peakWind).filter((wind) => wind > 0);
      return [{ year, globalTemperature: climateYearData.temperatureAnomaly, tropicalTemperature: climateYearData.tropicalTemperatureAnomaly, count: annualStorms.length, strongCount: winds.filter((wind) => wind >= 64).length, meanPeakWind: winds.length ? winds.reduce((sum, wind) => sum + wind, 0) / winds.length : null }];
    });
  }, [climate.yearlyClimate, storms]);
  const yFor = (lat: number) => projection([0, lat])?.[1] ?? 0;
  const xFor = (lon: number) => projection([normalizeLongitude(lon), 0])?.[0] ?? 0;

  return (
    <Stack as="main" minHeight="viewport">
      <TopBar links={[{ href: "#simulation", label: "시뮬레이션" }, { href: "#research", label: "연구 현황" }]} source={<><SourceBadge>NOAA IBTrACS v04r01</SourceBadge><Divider orientation="vertical" /><Text variant="caption" ink="secondary" as="span">Global · 1980–2026</Text></>} />

      <Stack gap="xl" id="top" className="page page-wide" paddingX="xl" paddingY="xl" width="full">
        <Inline justify="between" align="end" gap="lg" wrap as="section">
          <Stack gap="xs">
            <Text variant="title" as="h1">전 세계 열대저기압 아틀라스</Text>
            <Text variant="body" ink="secondary">1980년 이후 전 세계에서 관측된 열대저기압의 경로·강도와 기후 조건을 살펴봅니다.</Text>
          </Stack>
          <Link href={DATA_SOURCE} target="_blank" rel="noreferrer" underline="hover"><Inline gap="xs" align="center"><Text variant="caption" as="span">데이터 출처</Text><ExternalLink size={14} aria-hidden /></Inline></Link>
        </Inline>

        <Inline as="section" gap="md" align="center" wrap aria-label="자료 필터">
          <Inline gap="sm" align="center">
            <Label htmlFor="basin-select">해역</Label>
            <Select className="select-basin" id="basin-select" size="sm" shape="rounded" value={basin} onChange={(event) => setBasin(event.target.value)}>{["ALL", ...new Set(points.map((point) => point.basin))].map((code) => <Select.Option key={code} value={code}>{code === "ALL" ? "전 세계" : `${BASIN_LABELS[code] ?? "기타 해역"} (${code})`}</Select.Option>)}</Select>
          </Inline>
          <Inline gap="sm" align="center">
            <Label htmlFor="season-select">연도</Label>
            <Select className="select-fit" id="season-select" size="sm" value={season} onChange={(event) => { setSeason(event.target.value); setSelectedId(""); }}><Select.Option value="ALL">전체 연도</Select.Option>{seasons.map((year) => <Select.Option key={year} value={year}>{year}</Select.Option>)}</Select>
          </Inline>
          <Field className="filter-search" size="sm" aria-label="태풍 이름 검색" placeholder="태풍 이름 검색" leading={<Search size={14} aria-hidden />} clearable value={query} onChange={(event) => setQuery(event.target.value)} onClear={() => setQuery("")} />
        </Inline>

        {loadError && <Surface fill="sunken" border radius="sm" padding="md" role="status"><Text variant="caption" ink="warning">{loadError}</Text></Surface>}
        {!points.length && !loadError && <Inline justify="center" align="center" gap="sm" minHeight="xl"><Spinner label="불러오는 중" /><Text variant="caption" ink="secondary">NOAA 태풍 경로 자료를 불러오는 중입니다…</Text></Inline>}

        <Surface as="section" fill="raised" border radius="sm" aria-label="선택 범위 요약" className="stat-band">
          <Metric label="열대저기압 수" value={storms.length ? visibleStorms.length.toLocaleString() : "—"} note={`${season === "ALL" ? "1980년 이후" : `${season}년`} · 고유 SID 기준`} />
          <Metric label="경로 관측점" value={points.length ? pointsInSeason.toLocaleString() : "—"} note="대체로 3–6시간 간격" />
          <Metric label="최대 풍속" value={peak ? formatWind(peak) : "—"} note="WMO 기준 · 최대 지속풍" />
        </Surface>

        <Grid as="section" columns={{ base: 1, lg: "minmax(0, 1.7fr) minmax(16rem, .8fr)" }} gap="md" className="visual-grid">
          <Panel className="map-panel">
            <PanelHeading title="태풍 경로" caption={season === "ALL" ? "전체 연도 경로를 겹쳐 표시" : `${season}년 경로 · 태풍을 선택하면 강조됩니다`} aside={<Inline gap="xs" align="center" className="map-legend"><i className="legend-line" /><Text variant="caption" ink="tertiary" as="span">경로</Text><i className="legend-dot" /><Text variant="caption" ink="tertiary" as="span">중심 위치</Text></Inline>} />
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
              <Text variant="label" ink="tertiary" className="map-lat-label lat-top">60°N</Text><Text variant="label" ink="tertiary" className="map-lat-label lat-bottom">60°S</Text>
              {!visibleStorms.length && points.length > 0 && <Text variant="caption" ink="secondary" className="map-empty">조건에 맞는 태풍이 없습니다.</Text>}
            </div>
            <Inline justify="between" gap="md" className="map-footer"><Text variant="caption" ink="tertiary" as="span"><Text variant="caption" strong ink="primary" as="b">{visibleStorms.length.toLocaleString()}</Text>개 태풍 경로</Text><Text variant="caption" ink="tertiary" as="span">색상은 최대 풍속 구간을 나타냅니다</Text></Inline>
          </Panel>

          <Stack as="aside" gap="md">
            <Panel className="trend-panel">
              <PanelHeading title="연도별 발생 수" caption="전 세계 또는 선택 해역 · 고유 SID 기준" aside={<Badge variant="hairline" size="xs">1980—26</Badge>} />
              <div className="chart" role="img" aria-label="연도별 태풍 발생 수 막대 그래프">
                {yearly.map(({ year, count }) => <button key={year} className={`bar-wrap ${season === String(year) ? "chosen" : ""} ${year === yearly[yearly.length - 1]?.year ? "current-year" : ""}`} title={`${year}: ${count}개${year === 2026 ? " · 진행 중" : ""}`} onClick={() => setSeason(String(year))}>
                  <span className="bar-value">{count}</span><span className="bar" style={{ height: `${Math.max(3, count / maxCount * 100)}%` }} /><span className="bar-year">{year % 10 === 0 || year === yearly[yearly.length - 1]?.year ? String(year).slice(-2) : ""}</span>
                </button>)}
              </div>
              <Inline justify="between" className="chart-axis"><Text variant="label" ink="tertiary" as="span">{yearly[0]?.year ?? "—"}</Text><Text variant="label" ink="tertiary" as="span">연도 · 2026 진행 중</Text><Text variant="label" ink="tertiary" as="span">{yearly[yearly.length - 1]?.year ?? "—"}</Text></Inline>
            </Panel>
            <Panel className="selected-panel">
              <PanelHeading title="선택한 태풍" caption="지도 또는 목록에서 선택" />
              {activeStorm ? <Stack gap="md" className="storm-detail">
                <Inline justify="between" align="center"><Stack gap="xs"><Text variant="heading" as="p">{activeStorm.name}</Text><Text variant="caption" ink="tertiary">{activeStorm.season} · {activeStorm.basin} · {activeStorm.points.length}개 위치</Text></Stack><Badge accent="warning" variant="soft">{activeStorm.basin}</Badge></Inline>
                <Divider />
                <Grid columns={2} gap="md"><Stack gap="xs"><Text variant="caption" ink="tertiary">최대 풍속</Text><Text variant="body" strong numeric>{activeStorm.peakWind > 0 ? formatWind(activeStorm.peakWind) : "—"}</Text></Stack><Stack gap="xs"><Text variant="caption" ink="tertiary">최저 기압</Text><Text variant="body" strong numeric>{activeStorm.minPressure ? `${activeStorm.minPressure} hPa` : "—"}</Text></Stack></Grid>
                <Divider />
                <Inline gap="sm" align="center"><Text variant="caption" ink="secondary" numeric as="span">{activeStorm.start}</Text><Divider className="date-rule" /><Text variant="caption" ink="secondary" numeric as="span">{activeStorm.end}</Text></Inline>
              </Stack> : <Text variant="caption" ink="tertiary">표시할 태풍이 없습니다.</Text>}
            </Panel>
          </Stack>
        </Grid>

        <Stack as="section" gap="md" aria-label="태풍 경향 분석">
          <PanelHeading title="태풍 강도와 경로 경향" caption="연도별 · 선택한 해역 기준 · 열대저기압별 최대 풍속을 사용" />
          <Grid columns={{ base: 1, md: 2 }} gap="md">
            <Panel><PanelHeading level="subheading" title="평균·최대 풍속" caption="태풍별 WMO 최대 풍속의 연간 평균과 최댓값" />
              <LineChart years={analytics.years} label="연도별 태풍 최대 풍속 평균과 최댓값" unit="kt" series={[{ name: "평균", color: PUI.info, values: analytics.windByYear.map((item) => item.mean) }, { name: "최대", color: PUI.error, values: analytics.windByYear.map((item) => item.max) }]} />
            </Panel>
            <Panel><PanelHeading level="subheading" title="강한 태풍 빈도" caption="태풍별 최대 풍속이 기준 이상인 연간 개수" />
              <Box className="threshold-control"><SegmentControl size="xs" aria-label="풍속 기준 선택" value={String(windThreshold)} onValueChange={(value) => setWindThreshold(Number(value))}>{[34, 64, 96].map((threshold) => <SegmentControl.Item key={threshold} value={String(threshold)}>{threshold}+ kt</SegmentControl.Item>)}</SegmentControl></Box>
              <div className="threshold-chart">{analytics.windByYear.map((item) => { const max = Math.max(1, ...analytics.windByYear.map((row) => row.threshold)); return <div key={item.year} className="threshold-column" title={`${item.year}: ${item.threshold}개`}><i style={{ height: `${Math.max(2, item.threshold / max * 100)}%` }} /><span>{item.year % 10 === 0 || item.year === analytics.years.at(-1) ? String(item.year).slice(-2) : ""}</span></div>; })}</div>
              <Inline justify="between" className="chart-axis"><Text variant="label" ink="tertiary" as="span">{analytics.years[0] ?? "—"}</Text><Text variant="label" ink="tertiary" as="span">{windThreshold} kt 이상 · 태풍 수</Text><Text variant="label" ink="tertiary" as="span">{analytics.years.at(-1) ?? "—"}</Text></Inline>
            </Panel>
            <Panel className="track-analysis"><PanelHeading level="subheading" title="태풍 경로 중심 이동" caption="해역별로 태풍마다 평균 좌표를 구한 뒤 연도 평균" />
              <Grid columns={{ base: 1, md: 2 }} gap="lg" className="track-mini-grid"><Stack gap="xs"><Text variant="label" ink="tertiary">위도 (°)</Text><LineChart years={analytics.years} label="태풍별 평균 경로 중심 위도" unit="°" height={112} series={analytics.latitude} /></Stack><Stack gap="xs"><Text variant="label" ink="tertiary">경도 (°)</Text><LineChart years={analytics.years} label="태풍별 평균 경로 중심 경도" unit="°" height={112} series={analytics.longitude} /></Stack></Grid>
            </Panel>
          </Grid>
          <Text variant="caption" ink="tertiary" className="analysis-note">풍속 기준은 IBTrACS WMO_WIND(knot)이며 기관별 지속시간 기준 차이는 보정하지 않았습니다. 2026년은 진행 중입니다. 경로 중심은 태풍별 관측 좌표 평균으로 계산하므로 이동거리나 경로 밀도와는 다른 지표입니다.</Text>
        </Stack>

        <Stack as="section" gap="md" aria-label="기온과 태풍 발생·강도 관계">
          <PanelHeading title="기온 편차와 태풍 경향" caption="1980–2024년 · HadISDH 월별 기온 편차와 IBTrACS 연간 통계" aside={<SegmentControl size="sm" aria-label="기온 범위 선택" value={temperatureScope} onValueChange={(value) => setTemperatureScope(value as typeof temperatureScope)}><SegmentControl.Item value="globalTemperature">전 지구 평균</SegmentControl.Item><SegmentControl.Item value="tropicalTemperature">열대 위도대 (30°S–30°N)</SegmentControl.Item></SegmentControl>} />
          <Grid columns={{ base: 1, md: 2, lg: 3 }} gap="md">
            <TemperatureRelationshipChart rows={temperatureStormRows} temperatureScope={temperatureScope} metric="count" title="연간 태풍 발생 수" description="연간 발생 수" color={PUI.info} />
            <TemperatureRelationshipChart rows={temperatureStormRows} temperatureScope={temperatureScope} metric="strongCount" title="64 kt 이상 태풍 수" description="64 kt 이상 태풍 수" color={PUI.warning} />
            <TemperatureRelationshipChart rows={temperatureStormRows} temperatureScope={temperatureScope} metric="meanPeakWind" title="평균 최대풍속" description="태풍별 최대풍속 평균 (kt)" color={PUI.error} />
          </Grid>
          <Text variant="caption" ink="tertiary" className="analysis-note">점 하나는 한 해를 뜻하며 색은 10년 단위입니다. 기온은 관측된 격자만 위도 면적 가중해 계산하고, 태풍은 현재 선택한 해역 기준 고유 SID로 집계합니다. Pearson r은 원자료 상관, r*은 연도에 따른 직선 추세를 각각 제거한 잔차 간 상관입니다. 두 값 모두 인과관계를 뜻하지 않습니다. HadISDH의 2 m 지표면 공기 온도는 해수면온도(SST)를 대체하지 못하므로, 이 그래프는 전 지구적 동행 경향의 탐색용 비교입니다. 기후자료가 끝나는 2024년까지만 비교합니다.</Text>
        </Stack>

        <Stack as="section" gap="md" aria-label="전 세계 기온·습도와 기단 조건">
          <PanelHeading title="전 세계 기후 평년값과 기단 조건" caption="Met Office HadISDH.blend · 1973–2024 · 10° 격자 · 1991–2020 평년" aside={<Inline gap="sm" align="center" wrap>
            <Label htmlFor="climate-year">자료 시점</Label>
            <Select className="select-fit" id="climate-year" size="sm" value={climateYear} onChange={(event) => { setClimateYear(event.target.value); if (event.target.value === "NORMAL" && climateMetric === "airmass") setClimateMetric("temperature"); }}><Select.Option value="NORMAL">1991–2020 평년</Select.Option>{[...new Set(climateRows.map((row) => row.year))].sort((a, b) => b - a).map((year) => <Select.Option key={year} value={year}>{year}</Select.Option>)}</Select>
            <Label htmlFor="climate-month">월</Label>
            <Select className="select-fit" id="climate-month" size="sm" value={climateMonth} onChange={(event) => setClimateMonth(Number(event.target.value))}>{Array.from({ length: 12 }, (_, index) => <Select.Option key={index + 1} value={index + 1}>{`${index + 1}월`}</Select.Option>)}</Select>
          </Inline>} />
          {climateError && <Surface fill="sunken" border radius="sm" padding="md" role="status"><Text variant="caption" ink="warning">{climateError}</Text></Surface>}
          {!climateRows.length && !climateError ? <Panel className="climate-loading"><Inline justify="center" align="center" gap="sm"><Spinner label="불러오는 중" /><Text variant="caption" ink="secondary">기후 평년값·습도 자료를 불러오는 중입니다…</Text></Inline></Panel> : <Grid columns={{ base: 1, lg: "minmax(0, 1.35fr) minmax(0, .85fr)" }} gap="md">
            <Panel className="climate-map-panel">
              <PanelHeading level="subheading" title={climateMetric === "temperature" ? "2m 평균 기온" : climateMetric === "humidity" ? "2m 상대습도" : climateMetric === "upperair" ? "850 hPa 기온 평년" : "기단 열·수분 편차"} caption={climateMetric === "upperair" ? "1991–2020 상층 대기 평년 · 850 hPa" : climateYear === "NORMAL" ? "1991–2020 월별 기후 평년" : `${climateYear}년 ${climateMonth}월 · 평년 대비`} aside={<SegmentControl size="xs" aria-label="기후 지도 변수" value={climateMetric} onValueChange={(value) => setClimateMetric(value as typeof climateMetric)}><SegmentControl.Item value="temperature">기온</SegmentControl.Item><SegmentControl.Item value="humidity">습도</SegmentControl.Item><SegmentControl.Item value="airmass" disabled={climateYear === "NORMAL"}>기단 조건</SegmentControl.Item><SegmentControl.Item value="upperair">상층장</SegmentControl.Item></SegmentControl>} />
              <div className="climate-map-wrap"><ZoomableSvg className="climate-map" ariaLabel="전 세계 월별 기온, 상대습도, 기단 조건 및 상층 대기 지도"><rect width="820" height="460" className="ocean"/><path d={gridPath ?? ""} className="graticule"/><path d={LAND_PATH} className="land"/>{climateMapRows.map((row) => {
                const anomalyT = row.temperatureAnomaly; const anomalyRh = row.humidityAnomaly;
                const fill = climateMetric === "airmass" ? anomalyT >= 0 ? (anomalyRh >= 0 ? PUI.success : PUI.warning) : (anomalyRh >= 0 ? PUI.info : PUI.ink) : climateMetric === "temperature" ? row.temperature < 0 ? PUI.info : row.temperature < 15 ? tokens.color.ink.tertiary : row.temperature < 25 ? PUI.warning : PUI.error : climateMetric === "humidity" ? `color-mix(in srgb, ${PUI.info} ${Math.max(18, Math.min(100, row.humidity))}%, ${tokens.color.bg.raised})` : `color-mix(in srgb, ${PUI.info} ${Math.max(18, Math.min(100, (row.temperature + 35) * 1.5))}%, ${tokens.color.bg.raised})`;
                const latitudeLabel = `${Math.abs(row.lat)}°${row.lat < 0 ? "S" : "N"}`; const longitudeLabel = `${Math.abs(row.lon > 180 ? row.lon - 360 : row.lon)}°${row.lon > 180 || row.lon < 0 ? "W" : "E"}`;
                const extra = row.h500 !== null ? ` · RH850 ${row.humidity.toFixed(0)}% · Z500 ${row.h500.toFixed(0)} m · wind850 ${(Math.hypot(row.u850 ?? 0, row.v850 ?? 0)).toFixed(1)} m/s` : ` · ΔT ${anomalyT >= 0 ? "+" : ""}${anomalyT.toFixed(1)}°C · ΔRH ${anomalyRh >= 0 ? "+" : ""}${anomalyRh.toFixed(0)}%p`;
                return <circle key={row.gridId} cx={xFor(row.lon)} cy={yFor(row.lat)} r="3.3" fill={fill} stroke={tokens.color.bg.raised} strokeWidth=".7"><title>{latitudeLabel}, {longitudeLabel} · {row.temperature.toFixed(1)}°C · RH {row.humidity.toFixed(0)}%{extra}</title></circle>;
              })}</ZoomableSvg></div>
              <Inline justify="between" align="center" gap="sm" className="climate-legend">{climateMetric === "airmass" ? <><span><i style={{ background: PUI.success }} />온난·습윤</span><span><i style={{ background: PUI.warning }} />온난·건조</span><span><i style={{ background: PUI.info }} />한랭·습윤</span><span><i style={{ background: PUI.ink }} />한랭·건조</span></> : <><span><i className={`legend-gradient ${climateMetric === "humidity" ? "humidity-scale" : climateMetric === "upperair" ? "upperair-scale" : "temperature-scale"}`} />{climateMetric === "temperature" ? "저온 → 고온 (°C)" : climateMetric === "upperair" ? "850 hPa 기온 (°C)" : "저습 → 고습 (%)"}</span><span>{climateMetric === "upperair" ? climate.airMass.length : climate.displayRows.length}개 격자</span></>}</Inline>
            </Panel>
            <Stack gap="md">
              <Panel className="analytics-card"><PanelHeading level="subheading" title="전 지구 기온 편차" caption="1991–2020 월평년 대비 · 위도 면적 가중" /><LineChart years={climate.yearlyClimate.map((row) => row.year)} label="전 세계 2미터 기온 연평균 편차" unit="°C" height={140} series={[{ name: "기온 편차", color: PUI.warning, values: climate.yearlyClimate.map((row) => row.temperatureAnomaly) }]} /></Panel>
              <Panel className="analytics-card"><PanelHeading level="subheading" title="전 지구 상대습도 편차" caption="1991–2020 월평년 대비 · 위도 면적 가중" /><LineChart years={climate.yearlyClimate.map((row) => row.year)} label="전 세계 상대습도 연평균 편차" unit="%p" height={140} series={[{ name: "RH 편차", color: PUI.info, values: climate.yearlyClimate.map((row) => row.humidityAnomaly) }]} /></Panel>
            </Stack>
          </Grid>}
          <Text variant="caption" ink="tertiary" className="analysis-note">기온·습도는 HadISDH의 관측 기반 월 편차(1991–2020 평년)와 실제값을 함께 사용합니다. 관측이 없는 10° 격자는 보간하지 않아 지도에 빈칸으로 남습니다. 기단 조건 지도는 선택 연·월 편차 부호로 만든 탐색용 4분면(온난/한랭 × 습윤/건조)입니다. 상층장은 NCEP/NCAR의 850 hPa 기온·상대습도·바람과 500 hPa 지위고도 월평년입니다. 공기덩이의 발생지와 이동 경로를 추적한 공식 기단 분류는 아닙니다.</Text>
        </Stack>

        <Panel as="section" className="table-panel" padding="md">
          <PanelHeading title="열대저기압 목록" caption="이름, 기간, 관측된 최대 풍속 · 행을 누르면 경로가 강조됩니다" aside={<Text variant="caption" ink="tertiary" numeric>{visibleStorms.length.toLocaleString()}건</Text>} />
          <div className="table-scroll"><table className="data-table">
            <colgroup><col style={{ width: "8%" }} /><col style={{ width: "22%" }} /><col style={{ width: "8%" }} /><col style={{ width: "25%" }} /><col style={{ width: "18%" }} /><col style={{ width: "19%" }} /></colgroup>
            <thead><tr><th className="center">시즌</th><th>태풍</th><th className="center">해역</th><th>기간</th><th className="end">최대 풍속</th><th className="end">최저 기압</th></tr></thead>
            <tbody>{visibleStorms.slice(0, 100).map((storm) => <tr key={storm.sid} className={storm.sid === activeStorm?.sid ? "table-selected" : "table-clickable"} onClick={() => setSelectedId(storm.sid)}>
              <td className="center">{storm.season}</td><td><Text variant="body" strong as="span">{storm.name}</Text><Text variant="label" ink="tertiary" as="span" className="storm-id">{storm.sid}</Text></td><td className="center">{storm.basin}</td><td>{storm.start} – {storm.end}</td><td className="end"><span className={`wind-tag ${windClass(storm.peakWind)}`}>{storm.peakWind > 0 ? formatWind(storm.peakWind) : "—"}</span></td><td className="end">{storm.minPressure ? `${storm.minPressure} hPa` : "—"}</td>
            </tr>)}</tbody>
          </table></div>
          {visibleStorms.length > 100 && <Text variant="caption" ink="tertiary" as="p" className="table-more">목록에는 최신순 100개만 표시합니다. 연도나 해역 필터로 좁혀보세요.</Text>}
        </Panel>

        <Stack as="footer" gap="sm">
          <Inline gap="md" align="center" wrap>
            {[["Storms: NOAA NCEI · IBTrACS v04r01", DATA_SOURCE, "태풍 자료 설명"], ["Climate: Met Office · HadISDH.blend 1.5.1.2024f", HUMIDITY_SOURCE, "기후 자료 설명"], ["Upper air: NOAA PSL · NCEP/NCAR Reanalysis 1", CLIMATE_SOURCE, "상층 자료 설명"]].map(([text, href, label]) => <Inline key={href} gap="sm" align="center"><Text variant="caption" ink="tertiary" as="span">{text}</Text><Link href={href} target="_blank" rel="noreferrer" underline="hover"><Inline gap="xs" align="center"><Text variant="caption" as="span">{label}</Text><ExternalLink size={12} aria-hidden /></Inline></Link></Inline>)}
          </Inline>
          <Text variant="caption" ink="tertiary">IBTrACS는 열대저압부 등도 포함합니다. 2026년 태풍 시즌은 진행 중이며 최근 자료는 수정될 수 있습니다. 풍속은 WMO_WIND(knot)이며 기관별 평균 시간 차이는 보정하지 않았습니다. HadISDH는 빈 관측 격자를 보간하지 않아 지도에 빈칸이 남습니다.</Text>
        </Stack>
      </Stack>
    </Stack>
  );
}
