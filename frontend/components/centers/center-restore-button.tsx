"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { restoreCenterAction } from "@/actions/collection-centers.action";
import { useI18n } from "@/i18n/provider";

/**
 * Maintainer/admin control to restore an archived center back into the
 * public directory. The real authorization runs server-side in the action
 * (NFR-006); this button is UX only.
 */
export function CenterRestoreButton({ centerId }: { centerId: string }) {
  const { dict } = useI18n();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function run() {
    setError(null);
    startTransition(async () => {
      const res = await restoreCenterAction(centerId);
      if (res.error) {
        setError(res.error);
        return;
      }
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <Button size="sm" variant="primary" isPending={isPending} onPress={run}>
        {dict.centerArchive.restore}
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
