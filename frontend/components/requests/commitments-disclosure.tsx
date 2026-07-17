"use client";

import { Accordion } from "@heroui/react";

import { useI18n } from "@/i18n/provider";
import type { ItemCommitment } from "@/lib/requests.api";

import { ItemCommitments } from "./item-commitments";

/**
 * A single collapsible "see how others are contributing" panel that reveals the
 * item's public commitments. Sits next to the social-proof cue in the claim
 * area so a maker can peek at who is already helping without leaving the card.
 * Renders nothing when there are no live commitments to show.
 */
export function CommitmentsDisclosure({
  commitments,
  currentUsername = null,
}: {
  commitments: ItemCommitment[];
  /** Viewer's username, so their own commitments offer an edit shortcut. */
  currentUsername?: string | null;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;

  // Released commitments are back-out signals, not real progress — if none
  // remain there is nothing worth expanding, so skip the panel entirely.
  const hasLive = commitments.some((c) => c.status !== "released");
  if (!hasLive) {
    return null;
  }

  return (
    <Accordion className="w-full">
      <Accordion.Item id="commitments">
        <Accordion.Heading>
          <Accordion.Trigger>
            {t.seeOthersContributing}
            <Accordion.Indicator />
          </Accordion.Trigger>
        </Accordion.Heading>
        <Accordion.Panel>
          <Accordion.Body>
            <ItemCommitments
              commitments={commitments}
              currentUsername={currentUsername}
            />
          </Accordion.Body>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
}
