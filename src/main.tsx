import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { PaperProvider } from "@studio-baeks/paper-ui";
import { App } from "./App";
import { ResearchPage } from "./Research";
import "@studio-baeks/paper-ui/styles.css";
import "./styles.css";

function Root() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const update = () => setHash(window.location.hash);
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return hash === "#research" ? <ResearchPage /> : <App />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode><PaperProvider defaultTheme="light"><Root /></PaperProvider></StrictMode>,
);
