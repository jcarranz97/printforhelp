import type { Metadata, Viewport } from "next";
import { TopNav } from "@/components/layout/top-nav";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "PrintForHelp — Comunidad 3D al servicio de quien lo necesita",
  description:
    "Plataforma de coordinación para la comunidad de impresión 3D: " +
    "centros de acopio, peticiones y registro de piezas en producción.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full">
        <Providers>
          <TopNav />
          {children}
        </Providers>
      </body>
    </html>
  );
}
