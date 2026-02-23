import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Eval Builder",
  description: "Generate custom eval frameworks for LLM applications",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
