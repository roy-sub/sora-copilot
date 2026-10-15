import type { Metadata, Viewport } from "next";
import { Archivo, Outfit } from "next/font/google";
import "./globals.css";
import { PrefsProvider, themeInitScript } from "@/lib/prefs";
import { ToastProvider } from "@/components/Toast";

const archivo = Archivo({ subsets: ["latin", "latin-ext"], weight: ["400", "500", "600", "700"], variable: "--font-archivo", display: "swap" });
const outfit = Outfit({ subsets: ["latin", "latin-ext"], weight: ["300"], variable: "--font-outfit", display: "swap" });

export const metadata: Metadata = {
  title: { default: "SORA Copilot — From mission to dossier in minutes.", template: "%s · SORA Copilot" },
  description: "Describe the operation. The rules engine computes iGRC, GRC, ARC and SAIL, then emits an authority-ready dossier. Every line cites its rule.",
  openGraph: { images: ["/og-default.png"] },
};

export const viewport: Viewport = { themeColor: "#000000", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" className={`${archivo.variable} ${outfit.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <PrefsProvider>
          <ToastProvider>{children}</ToastProvider>
        </PrefsProvider>
      </body>
    </html>
  );
}
