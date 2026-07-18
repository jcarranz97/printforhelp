import type { Metadata, Viewport } from "next";

import { getCurrentUser } from "@/actions/auth.action";
import { ChooseUsernameModal } from "@/components/auth/choose-username-modal";
import { Footer } from "@/components/layout/footer";
import { LocaleSync } from "@/components/layout/locale-sync";
import { LocaleToast } from "@/components/layout/locale-toast";
import { MakerPrompt } from "@/components/layout/maker-prompt";
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
  const user = await getCurrentUser();
  // Google sign-ups must pick a username before doing anything else.
  const needsUsername = !!user && !user.username_chosen;
  // Ask the maker question only once the answer is unknown (no flag yet).
  const promptMaker =
    !!user && !needsUsername && user.flags?.maker === undefined;

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
            {user && (
              <LocaleSync
                effectiveLocale={locale}
                accountLocale={user.preferred_locale}
              />
            )}
            {!localeChosen && <LocaleToast />}
            {needsUsername && user && (
              <ChooseUsernameModal suggestion={user.username} />
            )}
            {promptMaker && <MakerPrompt />}
          </Providers>
        </I18nProvider>
      </body>
    </html>
  );
}
