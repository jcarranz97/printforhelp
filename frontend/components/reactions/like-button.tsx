"use client";

import { ToggleButton, Tooltip } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { FaHeart, FaRegHeart } from "react-icons/fa";

import { toggleReactionAction } from "@/actions/reactions.action";
import { useI18n } from "@/i18n/provider";
import type { ReactableEntityType } from "@/lib/reactions.api";

type LikeButtonProps = {
  entityType: ReactableEntityType;
  entityId: string;
  initialCount: number;
  initialReacted: boolean;
  /** Whether a session exists; guests are routed to /login on press. */
  isAuthenticated: boolean;
  size?: "sm" | "md" | "lg";
};

/**
 * Instagram-style heart toggle with a like count. The heart fills red when
 * the viewer has reacted; the count is shown only when > 0. Optimistic: the
 * UI flips immediately and reconciles with the server response. Guests see the
 * count and are sent to the login page when they try to react.
 */
export function LikeButton({
  entityType,
  entityId,
  initialCount,
  initialReacted,
  isAuthenticated,
  size = "sm",
}: LikeButtonProps) {
  const { dict } = useI18n();
  const t = dict.reactions;
  const router = useRouter();
  const [count, setCount] = useState(initialCount);
  const [reacted, setReacted] = useState(initialReacted);
  const [isPending, startTransition] = useTransition();

  function handleChange(nextSelected: boolean) {
    if (!isAuthenticated) {
      router.push("/login");
      return;
    }
    if (isPending) {
      return;
    }
    const previous = { count, reacted };
    // Optimistic flip.
    setReacted(nextSelected);
    setCount((c) => c + (nextSelected ? 1 : -1));
    startTransition(async () => {
      const res = await toggleReactionAction(entityType, entityId, previous);
      if (res.error === "auth") {
        router.push("/login");
        setReacted(previous.reacted);
        setCount(previous.count);
        return;
      }
      // Reconcile with the authoritative server count.
      setReacted(res.reacted);
      setCount(res.count);
    });
  }

  const tooltip = !isAuthenticated
    ? t.loginTooltip
    : reacted
      ? t.unlikeTooltip
      : t.likeTooltip;

  return (
    <Tooltip delay={300}>
      <ToggleButton
        isIconOnly={count <= 0}
        size={size}
        variant="ghost"
        isSelected={reacted}
        onChange={handleChange}
        aria-label={reacted ? t.unlikeAria : t.likeAria}
        // Instagram-style: only the heart fills red. Zero out the selected-state
        // accent background (the teal circle) by overriding the tokens the
        // component reads, and keep the count text in the normal foreground.
        className="gap-1.5 [--toggle-button-bg-selected:transparent] [--toggle-button-bg-selected-hover:transparent] [--toggle-button-bg-selected-pressed:transparent] [--toggle-button-fg-selected:inherit]"
      >
        {reacted ? (
          <FaHeart className="text-red-500" aria-hidden />
        ) : (
          <FaRegHeart aria-hidden />
        )}
        {count > 0 ? (
          <span className="text-sm font-medium tabular-nums">{count}</span>
        ) : null}
      </ToggleButton>
      <Tooltip.Content className="max-w-xs">
        <p>{tooltip}</p>
      </Tooltip.Content>
    </Tooltip>
  );
}
