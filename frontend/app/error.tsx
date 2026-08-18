"use client";

/**
 * Route-level error boundary.
 *
 * Without this file a single throw anywhere in the tree — a Server Component
 * fetch, or a client component reading a field the API did not send — unmounts
 * the whole React root and leaves the visitor a blank page with no way back.
 * Next only renders an error boundary that exists, so this is the containment
 * for every route under `app/`.
 *
 * This renders *inside* the root layout, so `useI18n` has its provider.
 * `global-error.tsx` is the last resort for throws in the layout itself, which
 * this boundary sits inside of and therefore cannot catch.
 */

import { Button } from "@heroui/react";
import { useEffect } from "react";

import { useI18n } from "@/i18n/provider";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { dict } = useI18n();
  const t = dict.errorBoundary;

  useEffect(() => {
    // The digest is the only handle correlating this render to the server log
    // line, since Next strips production error messages before they reach the
    // browser.
    console.error("Route error boundary:", error);
  }, [error]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-16 text-center">
      <h1 className="text-2xl font-semibold">{t.title}</h1>
      <p className="mt-3 text-default-500">{t.description}</p>
      {error.digest ? (
        <p className="mt-2 text-xs text-default-400">
          {t.digest} {error.digest}
        </p>
      ) : null}
      <div className="mt-8 flex justify-center gap-3">
        <Button onPress={() => reset()}>{t.retry}</Button>
        <Button
          variant="secondary"
          onPress={() => (window.location.href = "/")}
        >
          {t.home}
        </Button>
      </div>
    </main>
  );
}
