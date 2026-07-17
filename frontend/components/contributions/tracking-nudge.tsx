"use client";

import { Alert, Button } from "@heroui/react";
import Link from "next/link";

import { useI18n } from "@/i18n/provider";

/**
 * Recommends QR tracking to a maker who has not set it up yet.
 *
 * Tracking used to be reachable only from a bare "Ver rastreo" link at the
 * bottom of the card, which said nothing about what it was or why to bother —
 * so makers skipped it. This states the benefit in the maker's terms (the
 * center knows the box is yours; you see it arrive) at the point where labels
 * can still be attached, and leads with the one-label-per-box option: the
 * per-unit grid is what makes the feature look like an hour of scissor work.
 *
 * Deliberately `status="default"` (the quiet grey) rather than accent: the
 * next-step Alert directly above is the real call to action, and two accent
 * alerts stacked would compete. This is a suggestion, not the task.
 */
export function TrackingNudge({ contributionId }: { contributionId: string }) {
  const { dict } = useI18n();
  const t = dict.myContributions;
  const href = `/my-contributions/${contributionId}/tracking`;

  return (
    <Alert status="default">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Title>{t.trackingNudgeTitle}</Alert.Title>
        <Alert.Description>{t.trackingNudgeBody}</Alert.Description>
        <p className="mt-1 text-xs text-muted">{t.trackingNudgeHint}</p>
        {/* Mobile: the CTA belongs under the copy, not squeezed beside it. */}
        <Button
          className="mt-3 sm:hidden"
          size="sm"
          variant="secondary"
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render={(domProps: any) => <Link {...domProps} href={href} />}
        >
          {t.trackingNudgeCta}
        </Button>
      </Alert.Content>
      <Button
        className="hidden sm:block"
        size="sm"
        variant="secondary"
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        render={(domProps: any) => <Link {...domProps} href={href} />}
      >
        {t.trackingNudgeCta}
      </Button>
    </Alert>
  );
}
