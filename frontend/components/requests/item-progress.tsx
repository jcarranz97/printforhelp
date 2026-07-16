"use client";

import { useEffect, useRef, useState } from "react";

import type { RequestItem } from "@/lib/requests.api";
import { useI18n } from "@/i18n/provider";

/**
 * Fire once when the referenced element first scrolls into view. Used to defer
 * the progress-bar fill animation until the maker actually sees the bar, so it
 * animates on scroll rather than silently completing above the fold. Falls back
 * to "visible" immediately where IntersectionObserver is unavailable (e.g. SSR
 * hydration on old browsers).
 */
function useInView<T extends Element>(): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || inView) {
      return;
    }
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [inView]);
  return [ref, inView];
}

/**
 * Progress block for a request item (design "Refined stack" / 1a): a header
 * with the "X of Y pieces" line and a big percentage, a two-tone fill bar, and
 * a color-keyed legend. `committed` is the total pledged (claimed + at center);
 * `at_center` (delivered) is a subset drawn darker on top of it. Open-ended
 * items (no target) drop the percentage and "Remaining", and the bar fills
 * against the committed total to still show the delivered-vs-claimed split.
 *
 * Shared by the campaign detail card list and the standalone item page so both
 * render an identical bar.
 */
export function ItemProgress({
  p,
  unit,
}: {
  p: RequestItem["progress"];
  /** The item's chosen unit (e.g. "litros"); null = countable pieces. */
  unit: string | null;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const [barRef, inView] = useInView<HTMLDivElement>();
  const target = p.target_quantity;
  const committed = p.committed_quantity;
  const delivered = p.at_center_quantity;
  const hasTarget = target != null && target > 0;
  const unitWord = unit ?? t.progressUnit;
  // Fill against the target when set; otherwise the committed total so an
  // open-ended item still shows the delivered-vs-claimed split.
  const denom = hasTarget ? target : committed;
  const widthPct = (value: number) =>
    denom > 0 ? Math.min(100, (value / denom) * 100) : 0;
  const pctNum = hasTarget
    ? Math.round(Math.min(100, (committed / target) * 100))
    : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            {t.progressHeading}
          </div>
          <div className="mt-0.5 text-[13px]" style={{ color: "var(--muted)" }}>
            <strong style={{ color: "var(--foreground)" }}>{committed}</strong>{" "}
            {hasTarget ? `${t.progressOf} ${target} ${unitWord}` : unitWord}
          </div>
        </div>
        {pctNum !== null && (
          <div
            className="text-4xl font-extrabold leading-none"
            style={{
              color: "var(--accent-strong)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {pctNum}
            <span className="text-xl font-bold">%</span>
          </div>
        )}
      </div>
      <div
        ref={barRef}
        className="relative h-4 overflow-hidden rounded-full"
        style={{ background: "var(--card-border)" }}
        role="progressbar"
        aria-valuenow={committed}
        aria-valuemin={0}
        aria-valuemax={denom}
        aria-label={t.progressHeading}
      >
        <div
          className="pfh-bar-fill absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${widthPct(committed)}%`,
            background: "var(--accent)",
            transform: inView ? "scaleX(1)" : "scaleX(0)",
          }}
        />
        <div
          className="pfh-bar-fill absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${widthPct(delivered)}%`,
            background: "var(--accent-strong)",
            transform: inView ? "scaleX(1)" : "scaleX(0)",
            transitionDelay: "0.06s",
          }}
        />
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-[13px]">
        <span className="inline-flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-[3px]"
            style={{ background: "var(--accent-strong)" }}
          />
          {t.progressAtCenter} <strong className="ml-0.5">{delivered}</strong>
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-[3px]"
            style={{ background: "var(--accent)" }}
          />
          {t.progressClaimed} <strong className="ml-0.5">{committed}</strong>
        </span>
        {p.remaining !== null && (
          <span className="inline-flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-[3px]"
              style={{ background: "var(--card-border)" }}
            />
            {t.progressRemaining}{" "}
            <strong className="ml-0.5">{p.remaining}</strong>
          </span>
        )}
      </div>
    </div>
  );
}
