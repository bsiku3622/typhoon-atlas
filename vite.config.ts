import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { themeBootScript } from "@studio-baeks/paper-ui/theme-boot";
import { FONT_STYLESHEETS } from "@studio-baeks/paper-ui/tokens";

const paper = {
  name: "paper-ui-head",
  transformIndexHtml: () => [
    { tag: "script", children: themeBootScript({ defaultTheme: "light" }), injectTo: "head-prepend" as const },
    ...Object.values(FONT_STYLESHEETS).map((href) => ({ tag: "link", attrs: { rel: "stylesheet", href }, injectTo: "head" as const })),
  ],
};

export default defineConfig({ plugins: [react(), paper] });
