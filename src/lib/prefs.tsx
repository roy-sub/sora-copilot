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

export function PrefsProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [slots, setSlots] = useState(false);

  useEffect(() => {
    const t = document.documentElement.dataset.theme;
    if (t === "light" || t === "dark") setThemeState(t);
    setSlots(new URLSearchParams(location.search).get("slots") === "1");
  }, []);

  const setTheme = useCallback((t: Theme) => {
    document.documentElement.dataset.theme = t;
    setThemeState(t);
    try { localStorage.setItem(THEME_KEY, t); } catch {}
  }, []);

  return <Ctx.Provider value={{ theme, setTheme, slots }}>{children}</Ctx.Provider>;
}

export const usePrefs = () => useContext(Ctx);
