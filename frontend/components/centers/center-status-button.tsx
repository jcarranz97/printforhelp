"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { setCenterStatusAction } from "@/actions/collection-centers.action";
import { useI18n } from "@/i18n/provider";
import type { CollectionCenterStatus } from "@/lib/collection-centers.api";

/**
 * Flip a center's operational status between "active" (receiving donations)
 * and "inactive" (no longer receiving). The center stays public either way;
 * inactive just earns a "No recibe donaciones" badge. The real authorization
 * (effective member or maintainer/admin) runs server-side (NFR-006); this
 * button is UX only.
 */
export function CenterStatusButton({
  centerId,
  status,
}: {
  centerId: string;
  status: CollectionCenterStatus;
}) {
  const { dict } = useI18n();
  const t = dict.centerStatus;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const next: CollectionCenterStatus =
    status === "active" ? "inactive" : "active";

  function run() {
    setError(null);
    startTransition(async () => {
      const res = await setCenterStatusAction(centerId, next);
      if (res.error) {
        setError(res.error);
        return;
      }
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button size="sm" variant="secondary" isPending={isPending} onPress={run}>
        {status === "active" ? t.markInactive : t.markActive}
      </Button>
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
