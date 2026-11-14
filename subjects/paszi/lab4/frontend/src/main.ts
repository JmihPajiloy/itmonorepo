import { createElement, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./style.css";

createRoot(document.getElementById("root")!).render(
    createElement(StrictMode, null, createElement(App)),
);
