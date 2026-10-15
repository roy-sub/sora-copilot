"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "light";

interface Prefs {
  theme: Theme;
  setTheme: (t: Theme) => void;
  /** Dev mode for MediaSlot ids: ?slots=1 */
  slots: boolean;
  /**
   * The demo workspace — six fixture operations and a four-aircraft fleet.
   *
   * Off by default, so a real account lands on an empty dashboard. Turn it on with
   * `?demo=1`, or from the empty state. Anything it shows is labelled as demo data
   * computed in the browser, never as a determination.
   */
  demo: boolean;
  setDemo: (on: boolean) => void;
}

const Ctx = createContext<Prefs>({
  theme: "dark",
  setTheme: () => {},
  slots: false,
  demo: false,
  setDemo: () => {},
});

export const THEME_KEY = "sora.theme";
export const DEMO_KEY = "sora.demo";

/** Runs before paint so the sheets never flash the wrong stock. */
export const themeInitScript = `try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export function PrefsProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [slots, setSlots] = useState(false);
  const [demo, setDemoState] = useState(false);

  useEffect(() => {
    const t = document.documentElement.dataset.theme;
    if (t === "light" || t === "dark") setThemeState(t);

    const params = new URLSearchParams(location.search);
    setSlots(params.get("slots") === "1");

    // ?demo=1 turns it on and sticks; ?demo=0 turns it off again.
    const fromUrl = params.get("demo");
    if (fromUrl === "1" || fromUrl === "0") {
      const on = fromUrl === "1";
      setDemoState(on);
      try { localStorage.setItem(DEMO_KEY, on ? "1" : "0"); } catch {}
      return;
    }
    try { setDemoState(localStorage.getItem(DEMO_KEY) === "1"); } catch {}
  }, []);

  const setTheme = useCallback((t: Theme) => {
    document.documentElement.dataset.theme = t;
    setThemeState(t);
    try { localStorage.setItem(THEME_KEY, t); } catch {}
  }, []);

  const setDemo = useCallback((on: boolean) => {
    setDemoState(on);
    try { localStorage.setItem(DEMO_KEY, on ? "1" : "0"); } catch {}
  }, []);

  return (
    <Ctx.Provider value={{ theme, setTheme, slots, demo, setDemo }}>{children}</Ctx.Provider>
  );
}

export const usePrefs = () => useContext(Ctx);
