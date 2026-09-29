import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { PaperProvider } from "@studio-baeks/paper-ui";
import { App } from "./App";
import "@studio-baeks/paper-ui/styles.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode><PaperProvider defaultTheme="light"><App /></PaperProvider></StrictMode>,
);
