"use client";

import { Chip } from "@heroui/react";

import { useI18n } from "@/i18n/provider";
import type { ItemPriority } from "@/lib/requests.api";

/**
 * Chip color/variant per priority, escalating in weight so the tiers are
 * distinguishable at a glance: `high` is a solid red chip that pulls the eye,
 * `medium` a soft amber one, `low` a quiet grey one. Uses HeroUI's Chip rather
 * than hand-rolled Tailwind color utilities — the `*-100` palette classes are
 * not part of this theme, so a hand-rolled pill renders as bare text.
 */
const STYLES: Record<
  ItemPriority,
  {
    color: "danger" | "warning" | "default";
    variant: "primary" | "soft";
    arrow: string;
  }
> = {
  high: { color: "danger", variant: "primary", arrow: "↑" },
  medium: { color: "warning", variant: "soft", arrow: "" },
  low: { color: "default", variant: "soft", arrow: "↓" },
};

/** Chip showing how urgently an item is needed ("High priority"). */
export function PriorityBadge({
  priority,
  className,
}: {
  priority: ItemPriority;
  className?: string;
}) {
  const { dict } = useI18n();
  // Fall back rather than destructure blind: `priority` is typed non-null, but
  // it arrives from the API, so a backend older than migration 0047 (or any
  // future tier this build does not know) would otherwise throw
  // "Cannot destructure property 'color' of undefined" here. This badge renders
  // for every item on the campaign page, so that throw takes the whole page
  // down for everyone. `medium` is the column's own server_default.
  const { color, variant, arrow } = STYLES[priority] ?? STYLES.medium;

  return (
    <Chip color={color} variant={variant} size="sm" className={className}>
      {arrow ? (
        <span aria-hidden className="font-semibold">
          {arrow}
        </span>
      ) : (
        // A dot keeps the medium chip the same shape as the arrowed ones, so
        // the three tiers line up instead of jittering by a few pixels.
        <span
          aria-hidden
          className="inline-block h-1.5 w-1.5 rounded-full bg-current"
        />
      )}
      <Chip.Label>
        {dict.requestItem.priority[priority] ??
          dict.requestItem.priority.medium}
      </Chip.Label>
    </Chip>
  );
}
