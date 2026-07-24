/** ThemeProvider — 在 <html> 上设置 data-theme 并注入 CSS 变量 */

"use client";

import { useEffect } from "react";
import { type ThemeId, useUIStore } from "@/stores/ui-store";
import { themes } from "./themes";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const currentTheme = useUIStore((s) => s.currentTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", currentTheme);
    const tokens = themes[currentTheme]?.tokens;
    if (!tokens) return;
    for (const [key, value] of Object.entries(tokens)) {
      root.style.setProperty(key, value);
    }
  }, [currentTheme]);

  return <>{children}</>;
}

export function ThemeSelector() {
  const { currentTheme, setTheme } = useUIStore();
  return (
    <select
      value={currentTheme}
      onChange={(e) => setTheme(e.target.value as ThemeId)}
      className="rounded border px-2 py-1 text-xs bg-background"
    >
      {Object.entries(themes).map(([id, t]) => (
        <option key={id} value={id}>
          {t.name}
        </option>
      ))}
    </select>
  );
}
