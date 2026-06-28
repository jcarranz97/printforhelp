"use client";

import { Alert, Button } from "@heroui/react";
import { useState, useTransition } from "react";

import {
  revokeCenterVerificationAction,
  verifyCenterAction,
} from "@/actions/collection-centers.action";
import { useI18n } from "@/i18n/provider";

/**
 * Maintainer/admin control to verify an unverified center or revoke an
 * existing verification. The real authorization check runs server-side in
 * the action (NFR-006); this button is UX only.
 */
export function CenterVerifyButton({
  centerId,
  verified,
}: {
  centerId: string;
  verified: boolean;
}) {
  const { dict } = useI18n();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function run() {
    setError(null);
    startTransition(async () => {
      const res = verified
        ? await revokeCenterVerificationAction(centerId)
        : await verifyCenterAction(centerId);
      if (res.error) {
        setError(res.error);
      }
    });
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        size="sm"
        variant={verified ? "danger-soft" : "primary"}
        isPending={isPending}
        onPress={run}
      >
        {verified ? dict.centerVerify.revoke : dict.centerVerify.verify}
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
