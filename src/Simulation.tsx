import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, Pause, Play, Wind } from "lucide-react";

type CaseInfo = { id: string; label: string; note: string; dT: number; sst: number; pi: number; hours: number[]; vmax: number[]; pmin: number[]; rmw: number[] };
type FieldKey = "v" | "u" | "w" | "q" | "t";
type SimIndex = {
  cases: CaseInfo[];
  fields: Record<FieldKey, { min: number; max: number }>;
  planScale: { v: number; u: number; c: number };
  r: number[];
  z: number[];
  rPlan: number[];
  frames: number;
  frameHours: number;
};
type CaseData = { plan: Int16Array; section: Uint8Array };

const FIELD_ORDER: FieldKey[] = ["v", "u", "w", "q", "t"];
const FIELD_UI: Record<FieldKey, { label: string; unit: string; hint: string; range: [number, number]; stops: string[] }> = {
  v: { label: "접선풍", unit: "m/s", hint: "태풍 중심을 도는 바람", range: [0, 120], stops: ["#0c1c2c", "#14406b", "#2474c4", "#6fb6ee", "#d9f0ff"] },
  u: { label: "방사풍", unit: "m/s", hint: "음수는 중심으로 들어오는 바람, 양수는 나가는 바람", range: [-40, 40], stops: ["#1e6fc4", "#7fb4e6", "#e9e7e1", "#f0a27c", "#c94a1c"] },
  w: { label: "연직 바람", unit: "m/s", hint: "양수는 상승, 음수는 하강", range: [-12, 12], stops: ["#1e6fc4", "#7fb4e6", "#e9e7e1", "#f0a27c", "#c94a1c"] },
  q: { label: "구름과 비", unit: "g/kg", hint: "응결한 물의 양", range: [0, 5], stops: ["#0c1c2c", "#33516c", "#7f99ad", "#c3d1da", "#ffffff"] },
  t: { label: "기온 편차", unit: "K", hint: "같은 고도의 먼 외곽과의 차이", range: [-16, 16], stops: ["#1e6fc4", "#7fb4e6", "#e9e7e1", "#f0a27c", "#c94a1c"] },
};
const DAY_MS = 1100; // On-screen time per simulated day at normal speed.
const PLAN_RADIUS = 400;
const SECTION_RADIUS = 150;

function hexToRgb(hex: string): [number, number, number] {
  const value = parseInt(hex.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function buildLut(stops: string[]) {
  const colors = stops.map(hexToRgb);
  const lut = new Uint8ClampedArray(256 * 3);
  for (let i = 0; i < 256; i += 1) {
    const position = (i / 255) * (colors.length - 1);
    const low = Math.min(Math.floor(position), colors.length - 2);
    const frac = position - low;
    for (let c = 0; c < 3; c += 1) lut[i * 3 + c] = colors[low][c] + (colors[low + 1][c] - colors[low][c]) * frac;
  }
  return lut;
}

const LUTS = Object.fromEntries(FIELD_ORDER.map((key) => [key, buildLut(FIELD_UI[key].stops)])) as Record<FieldKey, Uint8ClampedArray>;
const SPEED_LUT = buildLut(["#5d90bd", "#9cc8ea", "#e8f6ff", "#ffffff", "#ffffff"]);

function useReducedMotion() {
  return useMemo(() => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);
}

function fieldValue(index: SimIndex, data: CaseData, key: FieldKey, frame: number, iz: number, ir: number) {
  const nz = index.z.length;
  const nr = index.r.length;
  const nv = FIELD_ORDER.length;
  const f0 = Math.min(Math.floor(frame), index.frames - 1);
  const f1 = Math.min(f0 + 1, index.frames - 1);
  const k = FIELD_ORDER.indexOf(key);
  const at = (f: number) => data.section[(f * nv + k) * nz * nr + iz * nr + ir];
  const raw = at(f0) + (at(f1) - at(f0)) * (frame - f0);
  const { min, max } = index.fields[key];
  return min + (raw / 255) * (max - min);
}

function planProfile(index: SimIndex, data: CaseData, frame: number) {
  const n = index.rPlan.length;
  const f0 = Math.min(Math.floor(frame), index.frames - 1);
  const f1 = Math.min(f0 + 1, index.frames - 1);
  const w = frame - f0;
  const v = new Float32Array(n);
  const u = new Float32Array(n);
  const c = new Float32Array(n);
  for (let i = 0; i < n; i += 1) {
    const read = (f: number, part: number) => data.plan[(f * 3 + part) * n + i];
    v[i] = (read(f0, 0) * (1 - w) + read(f1, 0) * w) * index.planScale.v;
    u[i] = (read(f0, 1) * (1 - w) + read(f1, 1) * w) * index.planScale.u;
    c[i] = (read(f0, 2) * (1 - w) + read(f1, 2) * w) * index.planScale.c;
  }
  return { v, u, c };
}

function nearestSeries(info: CaseInfo, hour: number) {
  const step = info.hours[1] - info.hours[0];
  const i = Math.max(0, Math.min(info.hours.length - 1, Math.round((hour - info.hours[0]) / step)));
  return { vmax: info.vmax[i], pmin: info.pmin[i], rmw: info.rmw[i] };
}

// Top-down view. Clouds are drawn from the radial profile; particles move with the lowest-level winds.
function PlanView({ index, data, frameRef, label, reduced }: { index: SimIndex; data: CaseData | null; frameRef: React.RefObject<number>; label: string; reduced: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const trailRef = useRef<HTMLCanvasElement | null>(null);
  const cloudRef = useRef<HTMLCanvasElement | null>(null);
  const particles = useRef<{ r: number; a: number; life: number }[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return undefined;
    const size = 420;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * ratio;
    canvas.height = size * ratio;
    const trail = document.createElement("canvas");
    trail.width = canvas.width;
    trail.height = canvas.height;
    trailRef.current = trail;
    const cloud = document.createElement("canvas");
    cloud.width = 210;
    cloud.height = 210;
    cloudRef.current = cloud;
    const pixel = cloud.getContext("2d")!;
    const image = pixel.createImageData(210, 210);
    const ctx = canvas.getContext("2d")!;
    const trailCtx = trail.getContext("2d")!;
    const scale = (size / 2) / PLAN_RADIUS;
    const spawn = () => ({ r: PLAN_RADIUS * Math.sqrt(0.02 + Math.random() * 0.98), a: Math.random() * Math.PI * 2, life: 200 + Math.random() * 400 });
    particles.current = Array.from({ length: 520 }, spawn);
    const dr = index.rPlan[1] - index.rPlan[0];
    const sample = (values: Float32Array, r: number) => {
      const x = Math.max(0, Math.min(values.length - 1.001, r / dr));
      const i = Math.floor(x);
      return values[i] + (values[i + 1] - values[i]) * (x - i);
    };
    let lastFrame = -1;
    let profile = planProfile(index, data, frameRef.current ?? 0);
    let rafId = 0;
    let rmw = 0;

    const drawCloud = () => {
      const n = 210;
      const buffer = image.data;
      for (let y = 0; y < n; y += 1) {
        for (let x = 0; x < n; x += 1) {
          const dx = (x + 0.5 - n / 2) / (n / 2);
          const dy = (y + 0.5 - n / 2) / (n / 2);
          const r = Math.sqrt(dx * dx + dy * dy) * PLAN_RADIUS;
          const i = (y * n + x) * 4;
          const opacity = r > PLAN_RADIUS * 1.42 ? 0 : 1 - Math.exp(-sample(profile.c, r) / 2.2);
          buffer[i] = 236;
          buffer[i + 1] = 241;
          buffer[i + 2] = 246;
          buffer[i + 3] = Math.min(235, opacity * 255);
        }
      }
      pixel.putImageData(image, 0, 0);
    };

    const render = () => {
      const current = frameRef.current ?? 0;
      if (Math.abs(current - lastFrame) > 0.04) {
        profile = planProfile(index, data, current);
        drawCloud();
        lastFrame = current;
        let best = 0;
        let bestV = -1;
        for (let i = 0; i < profile.v.length; i += 1) if (profile.v[i] > bestV) { bestV = profile.v[i]; best = i; }
        rmw = best * dr;
      }
      // Fade old trails, then advance particles with the true ratio of tangential to radial wind.
      trailCtx.setTransform(1, 0, 0, 1, 0, 0);
      trailCtx.globalCompositeOperation = "destination-out";
      trailCtx.fillStyle = "rgba(0,0,0,0.075)";
      trailCtx.fillRect(0, 0, trail.width, trail.height);
      trailCtx.globalCompositeOperation = "source-over";
      trailCtx.setTransform(ratio, 0, 0, ratio, (size / 2) * ratio, (size / 2) * ratio);
      trailCtx.lineWidth = 1;
      const seconds = reduced ? 0 : 150; // Model seconds advanced per drawn frame, for legibility.
      for (const particle of particles.current) {
        const v = sample(profile.v, particle.r);
        const u = sample(profile.u, particle.r);
        const speed = Math.sqrt(u * u + v * v);
        const x0 = particle.r * Math.cos(particle.a);
        const y0 = particle.r * Math.sin(particle.a);
        particle.a -= (v * seconds) / (Math.max(particle.r, 2) * 1000);
        particle.r += (u * seconds) / 1000;
        particle.life -= 1;
        if (particle.life <= 0 || particle.r > PLAN_RADIUS * 1.4 || particle.r < Math.max(rmw * 0.72, 4)) {
          Object.assign(particle, spawn());
          continue;
        }
        const x1 = particle.r * Math.cos(particle.a);
        const y1 = particle.r * Math.sin(particle.a);
        const shade = Math.min(255, Math.round((speed / 90) * 255)) * 3;
        trailCtx.strokeStyle = `rgba(${SPEED_LUT[shade]},${SPEED_LUT[shade + 1]},${SPEED_LUT[shade + 2]},0.85)`;
        trailCtx.beginPath();
        trailCtx.moveTo(x0 * scale, y0 * scale);
        trailCtx.lineTo(x1 * scale, y1 * scale);
        trailCtx.stroke();
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "#0d2438";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(cloud, 0, 0, canvas.width, canvas.height);
      ctx.drawImage(trail, 0, 0);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.strokeStyle = "rgba(255,255,255,0.28)";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 4]);
      for (const ring of [100, 200, 300]) {
        ctx.beginPath();
        ctx.arc(size / 2, size / 2, ring * scale, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.setLineDash([]);
      ctx.fillStyle = "rgba(255,255,255,0.72)";
      ctx.font = "11px Pretendard Variable, sans-serif";
      for (const ring of [100, 200, 300]) ctx.fillText(`${ring} km`, size / 2 + ring * scale + 3, size / 2 - 3);
      rafId = requestAnimationFrame(render);
    };
    render();
    return () => cancelAnimationFrame(rafId);
  }, [index, data, frameRef, reduced]);

  return <canvas ref={canvasRef} className="sim-plan" role="img" aria-label={`${label}: 위에서 본 모의 태풍`} />;
}

function SectionView({ index, data, field, frame, label }: { index: SimIndex; data: CaseData | null; field: FieldKey; frame: number; label: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const width = 560;
  const height = 280;
  const margin = { left: 34, right: 8, top: 8, bottom: 26 };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    const ctx = canvas.getContext("2d")!;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const nz = index.z.length;
    const rMaxIndex = index.r.findIndex((value) => value >= SECTION_RADIUS);
    const nr = rMaxIndex > 0 ? rMaxIndex : index.r.length;
    const off = document.createElement("canvas");
    off.width = nr * 2;
    off.height = nz;
    const pixel = off.getContext("2d")!;
    const image = pixel.createImageData(nr * 2, nz);
    const lut = LUTS[field];
    const [low, high] = FIELD_UI[field].range;
    for (let iz = 0; iz < nz; iz += 1) {
      for (let ir = 0; ir < nr; ir += 1) {
        const value = fieldValue(index, data, field, frame, iz, ir);
        const shade = Math.max(0, Math.min(255, Math.round(((value - low) / (high - low)) * 255))) * 3;
        for (const x of [nr - 1 - ir, nr + ir]) {
          const i = ((nz - 1 - iz) * nr * 2 + x) * 4;
          image.data[i] = lut[shade];
          image.data[i + 1] = lut[shade + 1];
          image.data[i + 2] = lut[shade + 2];
          image.data[i + 3] = 255;
        }
      }
    }
    pixel.putImageData(image, 0, 0);
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(off, margin.left, margin.top, plotW, plotH);
    // Secondary circulation arrows. Height is exaggerated on screen, so arrows show direction, not true slope.
    const xAt = (r: number) => margin.left + plotW / 2 + (r / SECTION_RADIUS) * (plotW / 2);
    const yAt = (z: number) => margin.top + plotH - (z / 20) * plotH;
    ctx.strokeStyle = field === "q" || field === "v" ? "rgba(255,255,255,0.75)" : "rgba(10,20,30,0.7)";
    ctx.lineWidth = 1;
    for (let iz = 1; iz < nz; iz += 3) {
      for (let ir = 3; ir < nr; ir += 5) {
        const u = fieldValue(index, data, "u", frame, iz, ir);
        const w = fieldValue(index, data, "w", frame, iz, ir);
        const dx = u * 0.5;
        const dy = -w * 1.6;
        const length = Math.hypot(dx, dy);
        if (length < 2) continue;
        const limit = Math.min(1, 16 / length);
        for (const sign of [-1, 1]) {
          const x0 = xAt(sign * index.r[ir]);
          const y0 = yAt(index.z[iz]);
          const x1 = x0 + sign * dx * limit;
          const y1 = y0 + dy * limit;
          const angle = Math.atan2(y1 - y0, x1 - x0);
          ctx.beginPath();
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
          ctx.lineTo(x1 - 3.5 * Math.cos(angle - 0.5), y1 - 3.5 * Math.sin(angle - 0.5));
          ctx.moveTo(x1, y1);
          ctx.lineTo(x1 - 3.5 * Math.cos(angle + 0.5), y1 - 3.5 * Math.sin(angle + 0.5));
          ctx.stroke();
        }
      }
    }
    // Axes
    const ink = getComputedStyle(canvas).getPropertyValue("--sim-axis") || "#55544f";
    ctx.fillStyle = ink;
    ctx.strokeStyle = ink;
    ctx.font = "11px Pretendard Variable, sans-serif";
    ctx.textAlign = "center";
    for (const r of [-150, -100, -50, 0, 50, 100, 150]) ctx.fillText(`${Math.abs(r)}`, xAt(r), height - 12);
    ctx.fillText("중심에서의 거리 (km)", margin.left + plotW / 2, height - 1);
    ctx.textAlign = "right";
    for (const z of [0, 5, 10, 15, 20]) ctx.fillText(`${z}`, margin.left - 5, yAt(z) + 4);
    ctx.save();
    ctx.translate(10, margin.top + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = "center";
    ctx.fillText("고도 (km)", 0, 0);
    ctx.restore();
  }, [index, data, field, frame, margin.left, margin.right, margin.top, margin.bottom]);

  const onMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!data) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - bounds.left) / bounds.width) * width;
    const py = ((event.clientY - bounds.top) / bounds.height) * height;
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    if (px < margin.left || px > width - margin.right || py < margin.top || py > margin.top + plotH) {
      setTip(null);
      return;
    }
    const r = Math.abs(((px - margin.left - plotW / 2) / (plotW / 2)) * SECTION_RADIUS);
    const z = ((margin.top + plotH - py) / plotH) * 20;
    const ir = index.r.reduce((best, value, i) => (Math.abs(value - r) < Math.abs(index.r[best] - r) ? i : best), 0);
    const iz = index.z.reduce((best, value, i) => (Math.abs(value - z) < Math.abs(index.z[best] - z) ? i : best), 0);
    const value = fieldValue(index, data, field, frame, iz, ir);
    setTip({
      x: (px / width) * 100,
      y: (py / height) * 100,
      text: `거리 ${index.r[ir].toFixed(0)} km, 고도 ${index.z[iz].toFixed(1)} km: ${FIELD_UI[field].label} ${value.toFixed(1)} ${FIELD_UI[field].unit}`,
    });
  };

  return (
    <div className="sim-section-wrap">
      <canvas ref={canvasRef} className="sim-section" role="img" aria-label={`${label}: ${FIELD_UI[field].label} 단면`} onPointerMove={onMove} onPointerLeave={() => setTip(null)} />
      {tip && <div className="sim-tip" style={{ left: `${tip.x}%`, top: `${tip.y}%` }}>{tip.text}</div>}
    </div>
  );
}

function ColorBar({ field }: { field: FieldKey }) {
  const ui = FIELD_UI[field];
  const middle = (ui.range[0] + ui.range[1]) / 2;
  return (
    <div className="sim-colorbar">
      <span className="sim-colorbar-title">{ui.label} ({ui.unit})</span>
      <div className="sim-colorbar-scale">
        <i style={{ background: `linear-gradient(90deg, ${ui.stops.join(",")})` }} />
        <span className="sim-colorbar-ticks"><b>{ui.range[0]}</b><b>{middle}</b><b>{ui.range[1]}</b></span>
      </div>
      <span className="sim-colorbar-hint">{ui.hint}</span>
    </div>
  );
}

function TimeChart({ a, b, hour, onSeek }: { a: CaseInfo; b: CaseInfo | null; hour: number; onSeek: (hour: number) => void }) {
  const width = 1080;
  const height = 250;
  const margin = { left: 44, right: 16, top: 12, bottom: 34 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const x = (h: number) => margin.left + (h / 360) * plotW;
  const y = (v: number) => margin.top + plotH - (v / 130) * plotH;
  const [hover, setHover] = useState<number | null>(null);
  const line = (info: CaseInfo) => info.hours.map((h, i) => `${i ? "L" : "M"}${x(h).toFixed(1)} ${y(info.vmax[i]).toFixed(1)}`).join(" ");
  const toHour = (event: React.PointerEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - bounds.left) / bounds.width) * width;
    return Math.max(0, Math.min(360, ((px - margin.left) / plotW) * 360));
  };
  const shown = hover ?? hour;
  const readA = nearestSeries(a, shown);
  const readB = b ? nearestSeries(b, shown) : null;
  return (
    <div className="sim-chart">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="시간에 따른 최대 풍속"
        onPointerMove={(event) => setHover(toHour(event))}
        onPointerLeave={() => setHover(null)}
        onClick={(event) => onSeek(toHour(event as unknown as React.PointerEvent<SVGSVGElement>))}
      >
        {[0, 30, 60, 90, 120].map((v) => <g key={v}><line className="sim-grid" x1={margin.left} x2={width - margin.right} y1={y(v)} y2={y(v)} /><text className="sim-axis" x={margin.left - 7} y={y(v) + 4} textAnchor="end">{v}</text></g>)}
        {[0, 3, 6, 9, 12, 15].map((d) => <text key={d} className="sim-axis" x={x(d * 24)} y={height - 14} textAnchor="middle">{d}</text>)}
        <text className="sim-axis" x={margin.left + plotW / 2} y={height - 1} textAnchor="middle">모의 시간 (일)</text>
        <text className="sim-axis" x={12} y={margin.top + plotH / 2} textAnchor="middle" transform={`rotate(-90 12 ${margin.top + plotH / 2})`}>최대 접선풍 (m/s)</text>
        <line className="sim-pi a" x1={margin.left} x2={width - margin.right} y1={y(a.pi)} y2={y(a.pi)} />
        {b && <line className="sim-pi b" x1={margin.left} x2={width - margin.right} y1={y(b.pi)} y2={y(b.pi)} />}
        <path className="sim-line a" d={line(a)} />
        {b && <path className="sim-line b" d={line(b)} />}
        <line className="sim-cursor" x1={x(hour)} x2={x(hour)} y1={margin.top} y2={margin.top + plotH} />
        {hover !== null && <line className="sim-hover" x1={x(hover)} x2={x(hover)} y1={margin.top} y2={margin.top + plotH} />}
        <circle className="sim-dot a" cx={x(shown)} cy={y(readA.vmax)} r={4.5} />
        {b && readB && <circle className="sim-dot b" cx={x(shown)} cy={y(readB.vmax)} r={4.5} />}
      </svg>
      <div className="sim-chart-legend">
        <span><i className="swatch a" /> {a.label}: {readA.vmax.toFixed(1)} m/s (PI {a.pi})</span>
        {b && readB && <span><i className="swatch b" /> {b.label}: {readB.vmax.toFixed(1)} m/s (PI {b.pi})</span>}
        <span className="sim-chart-time">{(shown / 24).toFixed(1)}일, 점선은 이론 PI, 그래프를 누르면 그 시각으로 이동</span>
      </div>
    </div>
  );
}

export function SimulationPage() {
  const reduced = useReducedMotion();
  const [index, setIndex] = useState<SimIndex | null>(null);
  const [failed, setFailed] = useState(false);
  const [store, setStore] = useState<Record<string, CaseData>>({});
  const [leftId, setLeftId] = useState("t0");
  const [rightId, setRightId] = useState("warm2");
  const [field, setField] = useState<FieldKey>("v");
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(!reduced);
  const frameRef = useRef(0);

  useEffect(() => {
    let active = true;
    fetch("research/sim/index.json")
      .then((response) => { if (!response.ok) throw new Error(String(response.status)); return response.json() as Promise<SimIndex>; })
      .then((data) => { if (active) setIndex(data); })
      .catch(() => { if (active) setFailed(true); });
    window.scrollTo(0, 0);
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!index) return;
    const nPlan = index.rPlan.length;
    const planCount = index.frames * 3 * nPlan;
    for (const id of [leftId, rightId]) {
      if (store[id]) continue;
      fetch(`research/sim/${id}.bin`)
        .then((response) => { if (!response.ok) throw new Error(String(response.status)); return response.arrayBuffer(); })
        .then((buffer) => {
          const plan = new Int16Array(buffer, 0, planCount);
          const section = new Uint8Array(buffer, planCount * 2);
          setStore((current) => ({ ...current, [id]: { plan, section } }));
        })
        .catch(() => setFailed(true));
    }
  }, [index, leftId, rightId, store]);

  useEffect(() => {
    frameRef.current = frame;
  }, [frame]);

  useEffect(() => {
    if (!playing || !index) return undefined;
    let last = performance.now();
    let rafId = 0;
    const step = (now: number) => {
      const days = (now - last) / DAY_MS;
      last = now;
      setFrame((current) => {
        const next = current + days * (24 / index.frameHours);
        if (next >= index.frames - 1) { setPlaying(false); return index.frames - 1; }
        return next;
      });
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [playing, index]);

  const hour = index ? (frame + 0.5) * index.frameHours : 0;
  const left = index?.cases.find((item) => item.id === leftId) ?? null;
  const right = index?.cases.find((item) => item.id === rightId) ?? null;
  const toFrame = useCallback((value: number) => (index ? Math.max(0, Math.min(index.frames - 1, value / index.frameHours - 0.5)) : 0), [index]);
  const togglePlay = () => {
    if (!index) return;
    if (!playing && frame >= index.frames - 1) setFrame(0);
    setPlaying(!playing);
  };

  return (
    <main className="atlas-shell">
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark"><Wind size={16} /></span> Cyclone Atlas</a>
        <nav className="topbar-right"><a className="topbar-link" href="#top">지도</a><span className="topbar-divider" /><a className="topbar-link" href="#research">연구 현황</a></nav>
      </header>
      <div className="page sim-page">
        <section className="sim-intro">
          <h1>모의 태풍을 비교해 보기</h1>
          <p>약한 소용돌이가 15일 동안 태풍으로 자라는 과정을 Rotunno–Emanuel(1987) 축대칭 모델로 계산한 결과입니다. 두 실험을 나란히 놓고 시간을 움직여 보세요.</p>
        </section>

        {failed && <p className="sim-message">시뮬레이션 자료를 불러오지 못했습니다. 페이지를 새로 고쳐 주세요.</p>}
        {!failed && !index && <p className="sim-message">시뮬레이션 자료를 불러오는 중입니다.</p>}

        {index && left && right && <>
          <div className="sim-controls">
            <button type="button" className="sim-play" onClick={togglePlay} aria-label={playing ? "일시 정지" : "재생"}>{playing ? <Pause size={18} /> : <Play size={18} />}</button>
            <label className="sim-slider">
              <span>{(hour / 24).toFixed(1)}일</span>
              <input type="range" min={0} max={index.frames - 1} step={0.01} value={frame} aria-label="모의 시간" onChange={(event) => { setPlaying(false); setFrame(Number(event.target.value)); }} />
            </label>
            <div className="sim-fields" role="group" aria-label="단면에 표시할 값">
              {FIELD_ORDER.map((key) => <button type="button" key={key} className={field === key ? "active" : ""} aria-pressed={field === key} onClick={() => setField(key)}>{FIELD_UI[key].label}</button>)}
            </div>
          </div>

          <div className="sim-stage">
            {[{ id: leftId, set: setLeftId, info: left, tone: "a" }, { id: rightId, set: setRightId, info: right, tone: "b" }].map((side) => {
              const read = nearestSeries(side.info, hour);
              return (
                <article className="sim-column" key={side.tone}>
                  <div className="sim-column-head">
                    <label>
                      <i className={`swatch ${side.tone}`} />
                      <select value={side.id} aria-label="실험 선택" onChange={(event) => side.set(event.target.value)}>
                        {index.cases.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                      </select>
                    </label>
                    <p>{side.info.note}</p>
                  </div>
                  <dl className="sim-readout">
                    <div><dt>최대 풍속</dt><dd>{read.vmax.toFixed(0)}<small>m/s</small></dd></div>
                    <div><dt>중심기압</dt><dd>{read.pmin.toFixed(0)}<small>hPa</small></dd></div>
                    <div><dt>최대풍 반경</dt><dd>{read.rmw.toFixed(0)}<small>km</small></dd></div>
                  </dl>
                  <PlanView index={index} data={store[side.id] ?? null} frameRef={frameRef} label={side.info.label} reduced={reduced} />
                  <SectionView index={index} data={store[side.id] ?? null} field={field} frame={frame} label={side.info.label} />
                </article>
              );
            })}
          </div>
          <ColorBar field={field} />

          <section className="sim-panel">
            <h2>시간에 따른 강도</h2>
            <TimeChart a={left} b={right} hour={hour} onSeek={(value) => { setPlaying(false); setFrame(toFrame(value)); }} />
          </section>

          <section className="sim-notes">
            <h2>보는 법과 주의할 점</h2>
            <ul>
              <li>위 그림의 입자는 모델의 최하층 바람으로 움직이고, 흰 부분은 응결한 물의 양을 나타냅니다. 움직임은 잘 보이도록 빠르게 재생합니다.</li>
              <li>축대칭 모델이라 모든 값이 중심에 대해 대칭입니다. 나선형 구름 띠, 태풍의 이동, 해양 냉각은 모델에 없습니다.</li>
              <li>풍속은 격자점의 순간값이어서 실제 태풍의 10분 평균 풍속과 비교할 수 없습니다. 절댓값보다 실험 간 차이를 보세요.</li>
              <li><b>온난화와 가까운 실험은 "바다와 대기 +2 K"입니다.</b> "대기만" 실험은 원인을 나누어 보기 위한 민감도 실험이므로, 온난화하면 태풍이 약해진다는 뜻으로 읽으면 안 됩니다.</li>
              <li>각 실험은 한 번의 실행입니다. 같은 조건을 5회 반복하면 8–15일 평균 강도의 표준편차는 조건에 따라 0.4~3.3 m/s이고, "바다와 대기 +2 K"(+8.5 ± 1.3%)와 "대기만 +2 K"(−20.9 ± 1.3%)의 변화는 이 잡음과 구분됩니다.</li>
              <li>"대기만 −2 K"는 정상 상태에 이르지 않고 정점 이후 환경이 크게 변합니다.</li>
            </ul>
            <p className="sim-links"><a href="#research">연구 결과 보기</a><a href="https://zenodo.org/records/10957526" target="_blank" rel="noreferrer">모델 코드 <ExternalLink size={12} /></a></p>
          </section>
        </>}
      </div>
    </main>
  );
}
