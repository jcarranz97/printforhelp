"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { reopenItemAction } from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";

/** Reopen a closed item from its detail page (requester/maintainer only). */
export function ReopenItemButton({
  requestId,
  itemId,
}: {
  requestId: string;
  itemId: string;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function run() {
    setError(null);
    startTransition(async () => {
      const res = await reopenItemAction(requestId, itemId);
      if (res.error) {
        setError(res.error);
        return;
      }
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button size="sm" onPress={run} isPending={pending}>
        {t.reopenItem}
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
