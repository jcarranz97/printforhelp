"use client";

import { Button, Tooltip } from "@heroui/react";
import { useState, useTransition } from "react";

import { toggleWatchAction } from "@/actions/notifications.action";
import { useI18n } from "@/i18n/provider";
import type { EntityType } from "@/lib/feed.api";

type WatchButtonProps = {
  entityType: EntityType;
  entityId: string;
  initialWatching: boolean;
};

/**
 * Watch / Watching toggle for an entity. Only rendered for logged-in
 * users; subscribing (or auto-subscribing by commenting) means the user
 * receives in-app notifications for activity on the entity.
 */
export function WatchButton({
  entityType,
  entityId,
  initialWatching,
}: WatchButtonProps) {
  const { dict } = useI18n();
  const t = dict.watch;
  const [watching, setWatching] = useState(initialWatching);
  const [isPending, startTransition] = useTransition();

  function toggle() {
    startTransition(async () => {
      const res = await toggleWatchAction(entityType, entityId, watching);
      setWatching(res.watching);
    });
  }

  return (
    <Tooltip delay={300}>
      <Button
        size="sm"
        variant={watching ? "secondary" : "tertiary"}
        isPending={isPending}
        aria-label={watching ? t.unwatchAria : t.watchAria}
        onPress={toggle}
      >
        {watching ? t.watching : t.watch}
      </Button>
      <Tooltip.Content className="max-w-xs">
        <p>{watching ? t.watchingTooltip : t.watchTooltip}</p>
      </Tooltip.Content>
    </Tooltip>
  );
}
