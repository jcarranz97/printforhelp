"use client";

import { Button } from "@heroui/react";
import { useEffect, useState } from "react";

import { useI18n } from "@/i18n/provider";
import type { TrackingVisibility } from "@/lib/tracking.api";

/**
 * Prominent, copyable public link for a tracking group. The public page
 * (`/track/{token}`) needs no login when visibility is public — this makes
 * that link obvious instead of hiding it behind the per-QR "open" links.
 */
export function ShareLink({
  token,
  visibility,
}: {
  token: string;
  visibility: TrackingVisibility;
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const [origin, setOrigin] = useState("");
  const [copied, setCopied] = useState(false);

  // Build the absolute URL on the client (the server has no request origin).
  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  const path = `/track/${token}`;
  const url = origin ? `${origin}${path}` : path;

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard may be unavailable (e.g. non-secure origin); ignore.
    }
  }

  if (visibility === "private") {
    return (
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">{t.shareTitle}</h2>
        <p className="text-sm text-muted">{t.sharePrivateNote}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">{t.shareTitle}</h2>
      <p className="text-sm text-muted">
        {visibility === "public" ? t.shareHintPublic : t.shareHintGroup}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <code className="flex-1 truncate rounded-lg border border-[var(--card-border)] bg-[var(--card)] px-3 py-2 text-sm">
          {url}
        </code>
        <Button type="button" variant="secondary" onPress={copy}>
          {copied ? t.shareCopied : t.shareCopy}
        </Button>
      </div>
    </div>
  );
}
