"use client";
import { Toast } from "@heroui/react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider defaultTheme="system" attribute="data-theme">
      {children}
      <Toast.Provider placement="bottom end" />
    </NextThemesProvider>
  );
}
