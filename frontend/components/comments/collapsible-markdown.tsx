"use client";

import { useEffect, useRef, useState } from "react";

import { Markdown } from "@/components/comments/markdown";
import { useI18n } from "@/i18n/provider";

// Collapsed height cap. Long descriptions are clamped to this so the
// comment thread stays near the top of the page (more interactions),
// with a "Show more" toggle to read the rest inline.
const COLLAPSED_MAX_PX = 360;
// Only offer the toggle when the content meaningfully exceeds the cap.
const OVERFLOW_BUFFER_PX = 24;

/**
 * Markdown description that collapses to a fixed max height with a fade and
 * a "Show more" / "Show less" toggle when the content overflows. Short
 * descriptions render normally (no toggle).
 */
export function CollapsibleMarkdown({ source }: { source: string }) {
  const { dict } = useI18n();
  const t = dict.description;
  const contentRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [overflows, setOverflows] = useState(false);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) {
      return;
    }
    const check = () =>
      setOverflows(el.scrollHeight > COLLAPSED_MAX_PX + OVERFLOW_BUFFER_PX);
    check();
    // Re-measure on reflow (width changes) and when images finish loading.
    const observer = new ResizeObserver(check);
    observer.observe(el);
    el.addEventListener("load", check, true);
    return () => {
      observer.disconnect();
      el.removeEventListener("load", check, true);
    };
  }, [source]);

  const clamped = !expanded;

  return (
    <div className="flex flex-col gap-2">
      <div
        ref={contentRef}
        className={`relative ${clamped ? "max-h-[360px] overflow-hidden" : ""}`}
      >
        <Markdown source={source} />
        {overflows && clamped && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[var(--background)] to-transparent" />
        )}
      </div>
      {overflows && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="w-fit text-sm font-medium text-[var(--accent-strong)] hover:underline"
        >
          {expanded ? t.showLess : t.showMore}
        </button>
      )}
    </div>
  );
}
