"use client";

import { Tooltip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import { useState } from "react";

import { useI18n } from "@/i18n/provider";

/**
 * Copies a shareable in-app URL to the clipboard with brief "copied" feedback.
 * The absolute URL is built from the current origin at click time so a copied
 * link works across environments (localhost, staging, production). The friendly
 * "share with a friend" nudge rides along as a left-placed tooltip so the
 * button itself stays compact in the card header.
 */
export function CopyLinkButton({ path }: { path: string }) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const [copied, setCopied] = useState(false);

  async function copy() {
    const url = `${window.location.origin}${path}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Clipboard may be unavailable (insecure context): drop the hash into the
      // address bar so the deep link is still selectable and copyable by hand.
      const hash = path.split("#")[1];
      if (hash) {
        window.location.hash = hash;
      }
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Tooltip delay={200}>
      <Tooltip.Trigger>
        <button
          type="button"
          onClick={copy}
          className={buttonVariants({ size: "sm", variant: "secondary" })}
        >
          {copied ? t.copyLinkCopied : t.copyLinkButton}
          <span aria-hidden="true"> 🔗</span>
        </button>
      </Tooltip.Trigger>
      <Tooltip.Content showArrow placement="left" className="max-w-[16rem]">
        <Tooltip.Arrow />
        {/* break-normal stops the tooltip's base style from splitting words
        mid-character (e.g. "par|t?"); it now wraps only at spaces. */}
        <p className="whitespace-normal break-normal">{t.sharePartPrompt}</p>
      </Tooltip.Content>
    </Tooltip>
  );
}
