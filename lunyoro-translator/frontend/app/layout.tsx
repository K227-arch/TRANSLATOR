import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import OfflineBanner from "@/components/OfflineBanner";
import ThemeProvider from "@/components/ThemeProvider";

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
    <html lang="en" className={`${inter.variable} dark`} suppressHydrationWarning>
      <head>
        <link rel="icon" href="/logo.png" type="image/png" />
        <link rel="apple-touch-icon" href="/logo.png" />
      </head>
      <body>
        <ThemeProvider>
          <OfflineBanner />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
