"use client";

import { Chip } from "@heroui/react";

import { useI18n } from "@/i18n/provider";
import type { CollectionCenterStatus } from "@/lib/collection-centers.api";

/**
 * Status chip showing whether a center is still receiving donations. Green
 * dot + "Recibiendo donaciones" when `active`, red dot + "No recibe
 * donaciones" when `inactive`. Used on both the directory cards and the
 * center detail header. The dot inherits the chip's text color via
 * `bg-current`, so it matches each color variant without extra tokens.
 */
export function CenterReceivingChip({
  status,
}: {
  status: CollectionCenterStatus;
}) {
  const { dict } = useI18n();
  const t = dict.centers;
  const receiving = status === "active";
  return (
    <Chip color={receiving ? "success" : "danger"} variant="soft" size="sm">
      <span
        aria-hidden
        className="inline-block h-1.5 w-1.5 rounded-full bg-current"
      />
      <Chip.Label>{receiving ? t.statusReceiving : t.notReceiving}</Chip.Label>
    </Chip>
  );
}
