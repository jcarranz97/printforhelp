"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { archivePartAction } from "@/actions/parts.action";
import { archiveSupplyAction } from "@/actions/supplies.action";
import { useI18n } from "@/i18n/provider";

/**
 * Archive (soft-delete) a part or supply so it leaves the catalog. The real
 * authorization runs server-side (effective owner or maintainer/admin,
 * NFR-006); this button is UX only. A first press reveals an inline confirm
 * step before the destructive call. Archiving is blocked while open Requests
 * reference the resource (the action surfaces that as an inline error).
 */
export function ArchiveResourceButton({
  resourceId,
  kind,
}: {
  resourceId: string;
  kind: "part" | "supply";
}) {
  const { dict } = useI18n();
  const t = dict.resourceArchive;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function run() {
    setError(null);
    startTransition(async () => {
      const res =
        kind === "part"
          ? await archivePartAction(resourceId)
          : await archiveSupplyAction(resourceId);
      if (res.error) {
        setError(res.error);
        return;
      }
      setConfirming(false);
      router.push(kind === "part" ? "/parts" : "/supplies");
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <span className="text-sm font-medium">{t.heading}</span>
      <p className="text-xs text-muted">
        {kind === "part" ? t.hintPart : t.hintSupply}
      </p>
      {confirming ? (
        <div className="flex flex-col items-start gap-2">
          <span className="text-sm">
            {kind === "part" ? t.confirmPart : t.confirmSupply}
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="danger"
              isPending={isPending}
              onPress={run}
            >
              {t.confirm}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              isDisabled={isPending}
              onPress={() => setConfirming(false)}
            >
              {t.cancel}
            </Button>
          </div>
        </div>
      ) : (
        <Button
          size="sm"
          variant="danger-soft"
          onPress={() => setConfirming(true)}
        >
          {kind === "part" ? t.archivePart : t.archiveSupply}
        </Button>
      )}
      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
    </div>
  );
}
