import type { ElementType, ReactNode } from "react";
import { Wind } from "lucide-react";
import { Badge, Box, Divider, Inline, Link, Stack, Surface, Text } from "@studio-baeks/paper-ui";

type NavLink = { href: string; label: ReactNode };

export function TopBar({ links, source }: { links: NavLink[]; source?: ReactNode }) {
  return (
    <Surface as="header" fill="raised" border="bottom" paddingX="xl" paddingY="sm">
      <Inline justify="between" align="center" gap="lg" wrap>
        <Link href="#top" underline="hover">
          <Inline gap="sm" align="center">
            <Box className="brand-mark"><Wind size={16} aria-hidden /></Box>
            <Text variant="body" strong>Cyclone Atlas</Text>
          </Inline>
        </Link>
        <Inline gap="md" align="center" wrap>
          {links.map((link) => <Link key={link.href} href={link.href} underline="hover"><Text variant="caption" strong as="span">{link.label}</Text></Link>)}
          {source && <>
            <Divider orientation="vertical" />
            {source}
          </>}
        </Inline>
      </Inline>
    </Surface>
  );
}

export function SourceBadge({ children }: { children: ReactNode }) {
  return <Badge accent="success" variant="ghost" dot>{children}</Badge>;
}

type PanelProps = { children?: ReactNode; padding?: "md" | "lg"; className?: string; as?: ElementType };

export function Panel({ children, padding = "lg", className, as = "article" }: PanelProps) {
  return <Surface as={as} fill="raised" border radius="sm" padding={padding} minWidth={0} className={className}>{children}</Surface>;
}

export function PanelHeading({ title, caption, level = "heading", aside }: { title: ReactNode; caption?: ReactNode; level?: "heading" | "subheading"; aside?: ReactNode }) {
  return (
    <Inline justify="between" align="start" gap="md" wrap>
      <Stack gap="xs">
        <Text variant={level} as={level === "heading" ? "h2" : "h3"}>{title}</Text>
        {caption && <Text variant="caption" ink="tertiary">{caption}</Text>}
      </Stack>
      {aside}
    </Inline>
  );
}

export function Metric({ label, value, note }: { label: ReactNode; value: ReactNode; note: ReactNode }) {
  return (
    <Box padding="md">
      <Stack gap="xs">
        <Text variant="caption" ink="secondary">{label}</Text>
        <Text variant="title" as="p" numeric>{value}</Text>
        <Text variant="caption" ink="tertiary">{note}</Text>
      </Stack>
    </Box>
  );
}
