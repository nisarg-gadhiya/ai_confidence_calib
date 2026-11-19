import { useEffect, useState } from "react";

const TOKENS = [
  "series-1", "series-2", "series-3", "series-4",
  "good", "warning", "critical", "muted",
  "text", "text-2", "grid", "axis", "surface", "accent",
];

function read() {
  const style = getComputedStyle(document.documentElement);
  const out = {};
  for (const t of TOKENS) out[t] = style.getPropertyValue(`--${t}`).trim();
  return out;
}

// Chart libraries need concrete colors, so resolve the CSS tokens and
// re-resolve whenever the theme flips.
export default function useThemeColors() {
  const [colors, setColors] = useState(read);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setColors(read());
    mq.addEventListener("change", update);
    const obs = new MutationObserver(update);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      mq.removeEventListener("change", update);
      obs.disconnect();
    };
  }, []);
  return colors;
}
