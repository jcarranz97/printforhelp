"use client";

import { useI18n } from "@/i18n/provider";

export type Milestone = {
  key: string;
  label: string;
  /** ISO timestamp when this milestone was reached, or null while pending. */
  at: string | null;
};

/** Amber used for the "released / cancelled" marker — readable on light and
 * dark cards alike, matching the warning chip. */
const RELEASED_COLOR = "#d97706";

/** Compact timestamp for a milestone label, e.g. "16 Jul, 18:20". */
function formatShort(iso: string, locale: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type StepState =
  | "done"
  | "next"
  | "blocked"
  | "future"
  | "released"
  | "cancelled";

/**
 * Filled progress rail for a contribution's lifecycle (design "Milestone bar",
 * option 1b): a continuous accent bar that fills to the last reached milestone,
 * with a node per step and its timestamp underneath. The first pending step
 * pulses as the next action.
 *
 * When the contribution was released the rail stops at the step it reached and
 * the step it was heading to becomes an amber "released" marker; anything past
 * that is shown as cancelled ("—"), making clear it will never be delivered.
 *
 * `blockedLabel` covers the case where the next milestone cannot be actioned
 * yet (e.g. delivery needs a drop-off center first): the node stops pulsing and
 * states the blocker instead of promising a step the maker cannot take.
 */
export function ContributionMilestones({
  steps,
  released = false,
  releasedAt = null,
  blockedLabel = null,
}: {
  steps: Milestone[];
  released?: boolean;
  /** When released, the timestamp shown on the release marker. */
  releasedAt?: string | null;
  /** Why the next milestone is not actionable yet; null when it is. */
  blockedLabel?: string | null;
}) {
  const { dict, locale } = useI18n();
  const t = dict.myContributions;
  const lastIndex = steps.length - 1;
  // First unreached step: the next action normally, or where a release stopped.
  const pendingIndex = steps.findIndex((s) => s.at === null);
  const nextIndex = released ? -1 : pendingIndex;
  const releasedIndex = released ? pendingIndex : -1;
  const lastDone = released
    ? releasedIndex - 1
    : nextIndex === -1
      ? lastIndex
      : nextIndex - 1;
  const fillPct =
    lastDone <= 0 || lastIndex <= 0 ? 0 : (lastDone / lastIndex) * 100;

  function stepState(i: number): StepState {
    if (released) {
      if (releasedIndex === -1) {
        return "done";
      }
      if (i < releasedIndex) {
        return "done";
      }
      return i === releasedIndex ? "released" : "cancelled";
    }
    if (steps[i].at !== null) {
      return "done";
    }
    if (i !== nextIndex) {
      return "future";
    }
    return blockedLabel ? "blocked" : "next";
  }

  return (
    <div>
      {/* Rail: track + fill + nodes. Extra side padding keeps the end nodes
      from clipping past the card edge. */}
      <div className="px-3 pt-1">
        <div className="relative h-5">
          <div
            className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 rounded-full"
            style={{ background: "var(--card-border)" }}
          />
          <div
            className="absolute left-0 top-1/2 h-2 -translate-y-1/2 rounded-full transition-[width] duration-500"
            style={{
              width: `${fillPct}%`,
              background: released
                ? "var(--muted)"
                : "linear-gradient(90deg, var(--accent-strong), var(--accent))",
            }}
          />
          {steps.map((s, i) => {
            const state = stepState(i);
            const x = lastIndex <= 0 ? 0 : (i / lastIndex) * 100;
            return (
              <div
                key={s.key}
                className="absolute top-1/2"
                style={{ left: `${x}%`, transform: "translate(-50%, -50%)" }}
              >
                {state === "next" ? (
                  <span
                    className="milestone-pulse block size-[22px] rounded-full"
                    style={{
                      background: "var(--card)",
                      border: "3px solid var(--accent-strong)",
                    }}
                  />
                ) : state === "released" ? (
                  <span
                    className="flex size-[22px] items-center justify-center rounded-full text-sm font-bold leading-none"
                    style={{
                      background: "var(--card)",
                      border: `2.5px solid ${RELEASED_COLOR}`,
                      color: RELEASED_COLOR,
                    }}
                  >
                    ✕
                  </span>
                ) : state === "done" ? (
                  <span
                    className="block size-[18px] rounded-full"
                    style={{
                      background: released
                        ? "var(--muted)"
                        : "var(--accent-strong)",
                      border: "3px solid var(--card)",
                    }}
                  />
                ) : (
                  <span
                    className="block size-4 rounded-full"
                    style={{
                      background: "var(--card)",
                      border: "2px dashed var(--card-border)",
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Labels + timestamps, aligned under their nodes (ends flush, middle
      centered). */}
      <div className="mt-2 flex text-xs">
        {steps.map((s, i) => {
          const state = stepState(i);
          const align =
            i === 0
              ? "text-left"
              : i === lastIndex
                ? "text-right"
                : "text-center";
          const labelColor =
            state === "next"
              ? "var(--accent-strong)"
              : state === "released"
                ? RELEASED_COLOR
                : state === "done" && !released
                  ? "var(--foreground)"
                  : "var(--muted)";
          const secondary =
            state === "released"
              ? releasedAt
                ? formatShort(releasedAt, locale)
                : ""
              : state === "cancelled"
                ? "—"
                : state === "blocked"
                  ? blockedLabel
                  : s.at
                    ? formatShort(s.at, locale)
                    : state === "next"
                      ? t.milestonePending
                      : t.milestoneUpcoming;
          return (
            <div key={s.key} className={`flex-1 ${align}`}>
              <span
                className={
                  state === "next" || state === "released"
                    ? "font-bold"
                    : "font-medium"
                }
                style={{
                  color: labelColor,
                  textDecoration:
                    state === "cancelled" ? "line-through" : undefined,
                }}
              >
                {state === "released" ? t.status.released : s.label}
              </span>
              <br />
              <span style={{ color: "var(--muted)" }}>{secondary}</span>
            </div>
          );
        })}
      </div>

      {released && (
        <p
          className="mt-2 text-xs font-medium"
          style={{ color: RELEASED_COLOR }}
        >
          {t.milestoneReleasedNote}
        </p>
      )}
    </div>
  );
}
