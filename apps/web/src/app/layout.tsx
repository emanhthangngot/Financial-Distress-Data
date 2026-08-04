import type { Metadata } from "next";
import { Be_Vietnam_Pro, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

/**
 * Be Vietnam Pro carries the interface because it is drawn for Vietnamese
 * diacritics: the vietnamese subset is requested explicitly so "Nguy cơ cao"
 * and "Đồng bộ lần cuối" render from one face instead of swapping mid-word.
 */
const beVietnamPro = Be_Vietnam_Pro({
  variable: "--font-be-vietnam-pro",
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

/** Numbers, tickers, revisions and SHAs only — never body copy. */
const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "DistressLens",
  description:
    "Theo dõi và đánh giá rủi ro tài chính doanh nghiệp. Nội dung phục vụ mục đích học tập.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      className={`${beVietnamPro.variable} ${ibmPlexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-paper-1 text-text-body">{children}</body>
    </html>
  );
}
