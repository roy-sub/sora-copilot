"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "light";

interface Prefs {
  theme: Theme;
  setTheme: (t: Theme) => void;
  /** Dev mode for MediaSlot ids: ?slots=1 */
  slots: boolean;
}

const Ctx = createContext<Prefs>({ theme: "dark", setTheme: () => {}, slots: false });

export const THEME_KEY = "sora.theme";

/** Runs before paint so the sheets never flash the wrong stock. */
export const themeInitScript = `try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

/** The stored theme, or null when there is none or storage is unavailable. */
function storedTheme(): Theme | null {
  try {
    const t = localStorage.getItem(THEME_KEY);
    return t === "light" || t === "dark" ? t : null;
  } catch {
    return null;
  }
}

export function PrefsProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [slots, setSlots] = useState(false);

  useEffect(() => {
    // Storage is the source of truth here, not the DOM — and the attribute is written
    // back rather than merely read.
    //
    // `themeInitScript` sets `data-theme` before paint, but a hydration mismatch makes
    // React re-render the root and reset the attributes to the ones the server emitted,
    // which is `data-theme="dark"`. That silently flipped a light-theme visitor back to
    // dark on roughly one hard load in seven, and reading the DOM here would have read
    // the clobbered value and agreed with it. Re-applying repairs it either way.
    const fallback = document.documentElement.dataset.theme;
    const t = storedTheme() ?? (fallback === "light" || fallback === "dark" ? fallback : null);
    if (t) {
      document.documentElement.dataset.theme = t;
      setThemeState(t);
    }
    setSlots(new URLSearchParams(location.search).get("slots") === "1");
  }, []);

  const setTheme = useCallback((t: Theme) => {
    document.documentElement.dataset.theme = t;
    setThemeState(t);
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch {
      // Private browsing or blocked storage: the theme still applies for this visit.
    }
  }, []);

  return <Ctx.Provider value={{ theme, setTheme, slots }}>{children}</Ctx.Provider>;
}

export const usePrefs = () => useContext(Ctx);
