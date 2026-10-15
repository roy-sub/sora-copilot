import type { Metadata, Viewport } from "next";
import { Archivo, Outfit } from "next/font/google";
import "./globals.css";
import { PrefsProvider, themeInitScript } from "@/lib/prefs";
import { AuthProvider } from "@/lib/auth";
import { QueryProvider } from "@/lib/query";
import { ToastProvider } from "@/components/Toast";

const archivo = Archivo({ subsets: ["latin", "latin-ext"], weight: ["400", "500", "600", "700"], variable: "--font-archivo", display: "swap" });
const outfit = Outfit({ subsets: ["latin", "latin-ext"], weight: ["300"], variable: "--font-outfit", display: "swap" });

// metadataBase resolves the social-card URL at build time; without it Next falls back
// to localhost and warns. NEXT_PUBLIC_SITE_URL is set per deployment.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://sora-copilot.pages.dev";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "SORA Copilot — From mission to dossier in minutes.", template: "%s · SORA Copilot" },
  description: "Describe the operation. The rules engine computes iGRC, GRC, ARC and SAIL, then emits an authority-ready dossier. Every line cites its rule.",
  openGraph: {
    type: "website",
    siteName: "SORA Copilot",
    title: "SORA Copilot — From mission to dossier in minutes.",
    description: "A symbolic rules engine computes the official SORA risk chain. Every line cites its rule.",
    images: [{ url: "/media/og-default.png", width: 1200, height: 630 }],
  },
  twitter: { card: "summary_large_image" },
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
          <AuthProvider>
            <QueryProvider>
              <ToastProvider>{children}</ToastProvider>
            </QueryProvider>
          </AuthProvider>
        </PrefsProvider>
      </body>
    </html>
  );
}
