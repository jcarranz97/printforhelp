"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import {
  archiveCenterAction,
  forceArchiveCenterAction,
} from "@/actions/collection-centers.action";
import { useI18n } from "@/i18n/provider";

/**
 * Archive (soft-delete) a collection center so it leaves the public
 * directory. Maintainers/admins use the force-archive path, which works on
 * any center; owners use the owner-side archive. The real authorization runs
 * server-side (NFR-006); this button is UX only. A first press reveals an
 * inline confirm step before the destructive call.
 */
export function CenterArchiveButton({
  centerId,
  isMaintainer,
}: {
  centerId: string;
  isMaintainer: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.centerArchive;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function run() {
    setError(null);
    startTransition(async () => {
      const res = isMaintainer
        ? await forceArchiveCenterAction(centerId)
        : await archiveCenterAction(centerId);
      if (res.error) {
        setError(res.error);
        return;
      }
      setConfirming(false);
      router.push("/centers");
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col items-start gap-2">
      {confirming ? (
        <div className="flex flex-col items-start gap-2">
          <span className="text-sm">{t.confirmQuestion}</span>
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
          {isMaintainer ? t.forceArchive : t.archive}
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
