import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink, Wind } from "lucide-react";
import { Badge, Table, Text } from "@studio-baeks/paper-ui";

type Tone = "done" | "running" | "pending" | "blocked" | "supported" | "rejected" | "inconclusive";
type Step = { id: string; title: string; status: Tone; detail: string };
type Hypothesis = { id: string; statement: string; status: Tone; evidence: string };
type Finding = { date: string; kind: string; title: string; detail: string };
type DataTable = { title: string; caption: string; columns: string[]; rows: (string | number)[][] };
type Figure = { src: string; title: string; caption: string };
type LinkItem = { label: string; href: string };
type ResearchStatus = {
  updatedAt: string;
  title: string;
  summary: string;
  notice: string;
  steps: Step[];
  hypotheses: Hypothesis[];
  findings: Finding[];
  tables: DataTable[];
  figures: Figure[];
  caveats: string[];
  links: LinkItem[];
};

const TONE: Record<Tone, { label: string; accent?: "success" | "info" | "warning" | "error" }> = {
  done: { label: "완료", accent: "success" },
  running: { label: "진행 중", accent: "info" },
  pending: { label: "예정" },
  blocked: { label: "막힘", accent: "error" },
  supported: { label: "지지", accent: "success" },
  rejected: { label: "지지되지 않음", accent: "warning" },
  inconclusive: { label: "판정 전" },
};

function StatusBadge({ tone }: { tone: Tone }) {
  const { label, accent } = TONE[tone];
  return <Badge accent={accent} variant="soft">{label}</Badge>;
}

export function ResearchPage() {
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`research/status.json?ts=${Date.now()}`)
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.json() as Promise<ResearchStatus>;
      })
      .then((data) => { if (active) setStatus(data); })
      .catch(() => { if (active) setFailed(true); });
    window.scrollTo(0, 0);
    return () => { active = false; };
  }, []);

  return (
    <main className="atlas-shell">
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark"><Wind size={16} /></span> Cyclone Atlas</a>
        <div className="topbar-right"><a className="topbar-link" href="#top"><ArrowLeft size={14} /> 지도로 돌아가기</a></div>
      </header>

      <div className="page research-page">
        {failed && <article className="panel research-panel"><Text variant="body">연구 현황을 불러오지 못했습니다.</Text></article>}
        {!failed && !status && <article className="panel research-panel"><Text variant="body">연구 현황을 불러오는 중입니다.</Text></article>}
        {status && <>
          <section className="research-intro">
            <span className="research-eyebrow">연구 현황 · {status.updatedAt} 기준</span>
            <h1>{status.title}</h1>
            <p>{status.summary}</p>
            <p className="research-notice">{status.notice}</p>
          </section>

          <section className="research-grid">
            <article className="panel research-panel">
              <div className="panel-heading"><div><Text variant="heading" as="h2">가설</Text><Text variant="caption">모델과 이론 계산으로 판정한다</Text></div></div>
              <ol className="research-list">
                {status.hypotheses.map((item) => <li key={item.id}>
                  <div className="research-row"><strong>{item.id}. {item.statement}</strong><StatusBadge tone={item.status} /></div>
                  <span>{item.evidence}</span>
                </li>)}
              </ol>
            </article>
            <article className="panel research-panel">
              <div className="panel-heading"><div><Text variant="heading" as="h2">진행 단계</Text><Text variant="caption">사례 → 통계 → 모의 → 해석</Text></div></div>
              <ol className="research-list">
                {status.steps.map((item) => <li key={item.id}>
                  <div className="research-row"><strong>{item.id}. {item.title}</strong><StatusBadge tone={item.status} /></div>
                  <span>{item.detail}</span>
                </li>)}
              </ol>
            </article>
          </section>

          <section className="panel research-panel">
            <div className="panel-heading"><div><Text variant="heading" as="h2">확인한 결과</Text><Text variant="caption">최근 순서 · 근거의 종류를 함께 표시</Text></div></div>
            <ul className="research-list">
              {status.findings.map((item) => <li key={`${item.date}-${item.title}`}>
                <div className="research-row"><strong>{item.title}</strong><span className="research-kind">{item.date} · {item.kind}</span></div>
                <span>{item.detail}</span>
              </li>)}
            </ul>
          </section>

          {status.tables.map((table) => <section className="panel research-panel" key={table.title}>
            <div className="panel-heading"><div><Text variant="heading" as="h2">{table.title}</Text><Text variant="caption">{table.caption}</Text></div></div>
            <div className="research-table">
              <Table>
                <Table.Header>{table.columns.map((column, index) => <Table.Column key={column} align={index === 0 ? undefined : "end"}>{column}</Table.Column>)}</Table.Header>
                <Table.Body>{table.rows.map((row) => <Table.Row key={String(row[0])}>
                  {row.map((cell, index) => <Table.Cell key={index} align={index === 0 ? undefined : "end"}>{cell}</Table.Cell>)}
                </Table.Row>)}</Table.Body>
              </Table>
            </div>
          </section>)}

          {status.figures.length > 0 && <section className="research-figures">
            {status.figures.map((figure) => <figure className="panel research-panel" key={figure.src}>
              <a href={figure.src} target="_blank" rel="noreferrer"><img src={figure.src} alt={figure.title} loading="lazy" /></a>
              <figcaption><strong>{figure.title}</strong><span>{figure.caption}</span></figcaption>
            </figure>)}
          </section>}

          <section className="panel research-panel">
            <div className="panel-heading"><div><Text variant="heading" as="h2">해석할 때 주의할 점</Text></div></div>
            <ul className="research-list research-caveats">{status.caveats.map((item) => <li key={item}><span>{item}</span></li>)}</ul>
          </section>

          <footer className="footer">
            {status.links.map((link) => <a key={link.href} href={link.href} target="_blank" rel="noreferrer">{link.label} <ExternalLink size={12} /></a>)}
          </footer>
        </>}
      </div>
    </main>
  );
}
