"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";

type Theme = "dark" | "light";

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  toggle: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");

  // On mount: read persisted preference, else respect OS preference
  useEffect(() => {
    let saved = "dark" as Theme;
    try {
      const stored = localStorage.getItem("theme") as Theme | null;
      if (stored === "light" || stored === "dark") {
        saved = stored;
      } else if (window.matchMedia("(prefers-color-scheme: light)").matches) {
        saved = "light";
      }
    } catch {
      // localStorage blocked (e.g. private browsing on some browsers)
    }
    setTheme(saved);
    applyTheme(saved);
  }, []);

  const applyTheme = (t: Theme) => {
    const html = document.documentElement;
    html.classList.remove("dark", "light");
    html.classList.add(t);
  };

  const toggle = useCallback(() => {
    setTheme(prev => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      applyTheme(next);
      try { localStorage.setItem("theme", next); } catch {}
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}
