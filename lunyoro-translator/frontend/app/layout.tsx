import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import OfflineBanner from "@/components/OfflineBanner";

// next/font inlines the font CSS — eliminates FOUT (flash of unstyled text)
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Runyoro-Rutooro Translator",
  description: "Professional English to Runyoro-Rutooro translation powered by AI",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "Runyoro Translator" },
};

export const viewport: Viewport = {
  themeColor: "#735c00",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <link rel="icon" href="/logo.png" type="image/png" />
        <link rel="apple-touch-icon" href="/logo.png" />
        {/* Material Symbols is self-hosted via @font-face in globals.css — no
            fonts.googleapis.com link. The Pi serves this app as a captive-portal
            access point where clients have no internet route, and an external
            stylesheet also *overrode* the local @font-face (it loads after Next's
            CSS), so all 75 icons fell back to the CDN and broke offline. */}
      </head>
      <body>
        <OfflineBanner />
        {children}
      </body>
    </html>
  );
}
