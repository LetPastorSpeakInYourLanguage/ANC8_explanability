import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ANC8 Prediction",
  description:
    "What best predicts eight or more antenatal care contacts in Ethiopia, and the earlier rungs ANC1+ and ANC4+.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
