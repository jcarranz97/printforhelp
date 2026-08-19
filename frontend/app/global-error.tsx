"use client";

/**
 * Last-resort boundary for throws in the root layout itself.
 *
 * This replaces the entire document, so it must render its own `<html>`/
 * `<body>` and cannot rely on anything the root layout sets up — no
 * `I18nProvider`, no HeroUI theme, no `globals.css`. Hence the inline styles
 * and the direct dictionary import instead of `useI18n`: if this file needed
 * the layout to work, it could not catch the layout failing.
 *
 * The locale is read straight from the cookie for the same reason. That is
 * the one place the choice is persisted, so copy stays translated even here.
 */

import { LOCALE_COOKIE, normalizeLocale } from "@/i18n/config";
import { en } from "@/i18n/dictionaries/en";
import { es } from "@/i18n/dictionaries/es";

function readLocale() {
  if (typeof document === "undefined") {
    return normalizeLocale(undefined);
  }
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${LOCALE_COOKIE}=([^;]*)`),
  );
  return normalizeLocale(match ? decodeURIComponent(match[1]) : undefined);
}

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const locale = readLocale();
  const t = (locale === "en" ? en : es).errorBoundary;

  return (
    <html lang={locale}>
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
          padding: "2rem",
          textAlign: "center",
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>{t.title}</h1>
          <p style={{ marginTop: "0.75rem", color: "#666" }}>{t.description}</p>
          {error.digest ? (
            <p
              style={{
                marginTop: "0.5rem",
                fontSize: "0.75rem",
                color: "#999",
              }}
            >
              {t.digest} {error.digest}
            </p>
          ) : null}
          <button
            onClick={() => reset()}
            style={{
              marginTop: "2rem",
              padding: "0.5rem 1.25rem",
              borderRadius: "0.5rem",
              border: "1px solid #ccc",
              background: "#fff",
              cursor: "pointer",
              font: "inherit",
            }}
          >
            {t.retry}
          </button>
        </div>
      </body>
    </html>
  );
}
