import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { Badge, Box, Divider, Grid, Inline, Link, Stack, Text } from "@studio-baeks/paper-ui";
import { Panel, PanelHeading, TopBar } from "./chrome";

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

  const list = (items: { key: string; title: string; trailing: ReactNode; detail: string }[], ordered = true) => (
    <Stack as={ordered ? "ol" : "ul"} gap="md" className="plain-list">
      {items.map((item, index) => <li key={item.key}>
        {index > 0 && <Divider />}
        <Stack gap="xs" className="list-item">
          {item.title && <Inline justify="between" align="start" gap="md" wrap><Text variant="body" strong as="span">{item.title}</Text>{item.trailing}</Inline>}
          <Text variant="body" ink="secondary">{item.detail}</Text>
        </Stack>
      </li>)}
    </Stack>
  );

  return (
    <Stack as="main" minHeight="viewport">
      <TopBar links={[{ href: "#simulation", label: "시뮬레이션" }, { href: "#top", label: <Inline gap="xs" align="center" as="span"><ArrowLeft size={14} aria-hidden />지도로 돌아가기</Inline> }]} />

      <Stack gap="md" className="page" paddingX="xl" paddingY="xl" maxWidth="container.content" width="full">
        {failed && <Panel><Text variant="body">연구 현황을 불러오지 못했습니다.</Text></Panel>}
        {!failed && !status && <Panel><Text variant="body">연구 현황을 불러오는 중입니다.</Text></Panel>}
        {status && <>
          <Stack as="section" gap="sm" maxWidth="measure.xl">
            <Text variant="caption" ink="tertiary">연구 현황 · {status.updatedAt} 기준</Text>
            <Text variant="title" as="h1">{status.title}</Text>
            <Text variant="body" ink="secondary">{status.summary}</Text>
            <Text variant="caption" ink="tertiary">{status.notice}</Text>
          </Stack>

          <Grid as="section" columns={{ base: 1, md: 2 }} gap="md" align="start">
            <Panel>
              <Stack gap="md">
                <PanelHeading title="가설" caption="모델과 이론 계산으로 판정한다" />
                {list(status.hypotheses.map((item) => ({ key: item.id, title: `${item.id}. ${item.statement}`, trailing: <StatusBadge tone={item.status} />, detail: item.evidence })))}
              </Stack>
            </Panel>
            <Panel>
              <Stack gap="md">
                <PanelHeading title="진행 단계" caption="사례 → 통계 → 모의 → 해석" />
                {list(status.steps.map((item) => ({ key: item.id, title: `${item.id}. ${item.title}`, trailing: <StatusBadge tone={item.status} />, detail: item.detail })))}
              </Stack>
            </Panel>
          </Grid>

          <Panel as="section">
            <Stack gap="md">
              <PanelHeading title="확인한 결과" caption="최근 순서 · 근거의 종류를 함께 표시" />
              {list(status.findings.map((item) => ({ key: `${item.date}-${item.title}`, title: item.title, trailing: <Text variant="caption" ink="tertiary" as="span">{item.date} · {item.kind}</Text>, detail: item.detail })), false)}
            </Stack>
          </Panel>

          {status.tables.map((table) => <Panel as="section" key={table.title}>
            <Stack gap="md">
              <PanelHeading title={table.title} caption={table.caption} />
              <Box overflowX="auto">
                <table className="data-table">
                  <thead><tr>{table.columns.map((column, index) => <th key={column} className={index === 0 ? undefined : "end"}>{column}</th>)}</tr></thead>
                  <tbody>{table.rows.map((row) => <tr key={String(row[0])}>
                    {row.map((cell, index) => <td key={index} className={index === 0 ? undefined : "end"}>{cell}</td>)}
                  </tr>)}</tbody>
                </table>
              </Box>
            </Stack>
          </Panel>)}

          {status.figures.length > 0 && <Grid as="section" columns={{ base: 1, md: 2 }} gap="md">
            {status.figures.map((figure) => <Panel as="figure" className="figure-panel" key={figure.src}>
              <Stack gap="sm">
                <Link href={figure.src} target="_blank" rel="noreferrer"><img className="research-figure" src={figure.src} alt={figure.title} loading="lazy" /></Link>
                <Stack as="figcaption" gap="xs"><Text variant="body" strong as="span">{figure.title}</Text><Text variant="caption" ink="secondary" as="span">{figure.caption}</Text></Stack>
              </Stack>
            </Panel>)}
          </Grid>}

          <Panel as="section">
            <Stack gap="md">
              <PanelHeading title="해석할 때 주의할 점" />
              {list(status.caveats.map((item) => ({ key: item, title: "", trailing: null, detail: item })), false)}
            </Stack>
          </Panel>

          <Inline as="footer" gap="md" wrap>
            {status.links.map((link) => <Link key={link.href} href={link.href} target="_blank" rel="noreferrer" underline="hover"><Inline gap="xs" align="center"><Text variant="caption" as="span">{link.label}</Text><ExternalLink size={12} aria-hidden /></Inline></Link>)}
          </Inline>
        </>}
      </Stack>
    </Stack>
  );
}
