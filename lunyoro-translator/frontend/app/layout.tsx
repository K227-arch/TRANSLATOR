import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Runyoro / Rutooro Translator",
  description: "Translate English to Runyoro and Rutooro",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
