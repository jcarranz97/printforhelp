"use client";

import { Alert } from "@heroui/react";
import type { ReactNode } from "react";

import { useI18n } from "@/i18n/provider";

/**
 * What the maker has to do next on a contribution:
 *  - "print"   — committed, still needs printing
 *  - "center"  — ready to hand over, but no drop-off center picked yet
 *  - "deliver" — printed and a center is set: take it there
 *  - "done"    — delivered/received; nothing left to do
 */
export type NextStepKind = "print" | "center" | "deliver" | "done";

/**
 * Alert status per step: outstanding work reads as accent, completion as
 * success. The status also picks the indicator icon, which is why this uses
 * Alert's own — emoji and hand-drawn glyphs sit outside the design system.
 */
const STATUS: Record<NextStepKind, "accent" | "success"> = {
  print: "accent",
  center: "accent",
  deliver: "accent",
  done: "success",
};

/**
 * The "next step" banner from the milestone-bar design (option 1b): one line
 * telling the maker exactly what to do now, with the action right next to it.
 * Sits between the milestone bar and the drop-off panel, so the rail says where
 * you are and this says what's next. Built on the HeroUI Alert so it matches
 * every other alert on the site.
 */
export function ContributionNextStep({
  kind,
  detail,
  action,
}: {
  kind: NextStepKind;
  /** Secondary line — the center name, or a hint. */
  detail?: string | null;
  /** The lifecycle button for this step, when there is one to press. */
  action?: ReactNode;
}) {
  const { dict } = useI18n();
  const t = dict.myContributions;
  const title: Record<NextStepKind, string> = {
    print: t.nextStepPrint,
    center: t.nextStepCenter,
    deliver: t.nextStepDeliver,
    done: t.nextStepDone,
  };

  return (
    <Alert status={STATUS[kind]}>
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Title>{title[kind]}</Alert.Title>
        {detail && <Alert.Description>{detail}</Alert.Description>}
        {/* On a phone the action stacks under the copy. As a flex sibling of
        the content (the desktop layout below) it claims its own width and
        squeezes the title into a one-word-per-line column. Rendering it in
        both places and letting the breakpoint pick is HeroUI's documented
        pattern for an Alert with an action — only one is ever visible. */}
        {action && <div className="mt-3 sm:hidden">{action}</div>}
      </Alert.Content>
      {action && <div className="hidden shrink-0 sm:block">{action}</div>}
    </Alert>
  );
}
