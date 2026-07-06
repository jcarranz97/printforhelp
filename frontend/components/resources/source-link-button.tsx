"use client";

import { buttonVariants } from "@heroui/styles";

import { useI18n } from "@/i18n/provider";
import { sourceProvider } from "@/lib/source-link";

/**
 * Provider-aware call to action linking to a Resource's external source /
 * download URL (e.g. "Take me to MakerWorld"). Shared by the part detail page,
 * the request campaign + item pages, and the post-commit thank-you so a maker
 * can grab the file straight from wherever they committed.
 */
export function SourceLinkButton({ url }: { url: string }) {
  const { dict } = useI18n();
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={buttonVariants({ size: "sm" })}
    >
      {dict.partDetail.sourceLinks[sourceProvider(url)]}
      <span aria-hidden="true"> ↗</span>
    </a>
  );
}
