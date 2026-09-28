"use client";

import { createContext, useContext, useEffect, useState } from "react";

/**
 * Display preferences (dark/light, font size, typeface), from the house design's
 * theme-provider, plus a presentation switch for projecting the studio in a meeting:
 * it enlarges everything by one step without changing any layout. Stored per device.
 */

type Theme = "light" | "dark";
type FontSize = "small" | "normal" | "large" | "xlarge";
type FontFamily = "sans" | "system" | "serif";

interface ThemeState {
  theme: Theme;
  fontSize: FontSize;
  fontFamily: FontFamily;
  present: boolean;
  toggle: () => void;
  togglePresent: () => void;
  setFontSize: (v: FontSize) => void;
  setFontFamily: (v: FontFamily) => void;
}

const ThemeContext = createContext<ThemeState | null>(null);

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}

const KEYS = { theme: "anc-theme", size: "anc-font-size", family: "anc-font-family" };

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private window: the preference simply is not remembered */
  }
}

function applyAttrs(theme: Theme, fontSize: FontSize, fontFamily: FontFamily, present: boolean) {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  if (fontSize === "normal") root.removeAttribute("data-font-size");
  else root.setAttribute("data-font-size", fontSize);
  if (fontFamily === "sans") root.removeAttribute("data-font-family");
  else root.setAttribute("data-font-family", fontFamily);
  if (present) root.setAttribute("data-present", "on");
  else root.removeAttribute("data-present");
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");
  const [fontSize, setFontSizeState] = useState<FontSize>("normal");
  const [fontFamily, setFontFamilyState] = useState<FontFamily>("sans");
  const [present, setPresent] = useState(false);

  useEffect(() => {
    const t = (read(KEYS.theme) as Theme | null) ?? "light";
    const s = (read(KEYS.size) as FontSize | null) ?? "normal";
    const f = (read(KEYS.family) as FontFamily | null) ?? "sans";
    setTheme(t);
    setFontSizeState(s);
    setFontFamilyState(f);
    applyAttrs(t, s, f, false);
  }, []);

  const toggle = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    write(KEYS.theme, next);
    applyAttrs(next, fontSize, fontFamily, present);
  };

  const togglePresent = () => {
    const next = !present;
    setPresent(next);
    applyAttrs(theme, fontSize, fontFamily, next);
  };

  const setFontSize = (v: FontSize) => {
    setFontSizeState(v);
    write(KEYS.size, v);
    applyAttrs(theme, v, fontFamily, present);
  };

  const setFontFamily = (v: FontFamily) => {
    setFontFamilyState(v);
    write(KEYS.family, v);
    applyAttrs(theme, fontSize, v, present);
  };

  return (
    <ThemeContext.Provider
      value={{ theme, fontSize, fontFamily, present, toggle, togglePresent, setFontSize, setFontFamily }}
    >
      {children}
    </ThemeContext.Provider>
  );
}
