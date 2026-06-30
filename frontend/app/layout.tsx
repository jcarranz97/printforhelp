import type { Metadata, Viewport } from "next";

import { Footer } from "@/components/layout/footer";
import { LocaleToast } from "@/components/layout/locale-toast";
import { TopNav } from "@/components/layout/top-nav";
import { PageNoticeBanner } from "@/components/notices/page-notice-banner";
import { I18nProvider } from "@/i18n/provider";
import { getServerI18n } from "@/i18n/server";

import { Providers } from "./providers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return {
    title: dict.meta.title,
    description: dict.meta.description,
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { locale, dict, localeChosen } = await getServerI18n();

  return (
    <html lang={locale} className="h-full antialiased" suppressHydrationWarning>
      <body className="flex min-h-full flex-col">
        <I18nProvider locale={locale} dict={dict}>
          <Providers>
            <div className="sticky top-0 z-40 bg-[var(--background)]">
              <TopNav />
              <PageNoticeBanner />
            </div>
            <div className="flex-1">{children}</div>
            <Footer />
            {!localeChosen && <LocaleToast />}
          </Providers>
        </I18nProvider>
      </body>
    </html>
  );
}
