import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "TRADEMERC - Trading Platform",
  description: "Plataforma de trading algorítmico TRADEMERC",
  icons: {
    icon: "/icon.png",
    shortcut: "/favicon.ico",
    apple: "/icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <head>
        <link rel="icon" href="/icon.png" sizes="any" />
      </head>
      <body className="bg-[#008080] min-h-screen p-2 sm:p-4 text-black">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
