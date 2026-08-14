"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useActionState, useEffect } from "react";

import {
  type TrackingState,
  generateCommitmentTrackingAction,
} from "@/actions/tracking.action";
import { useI18n } from "@/i18n/provider";

const initialState: TrackingState = { error: null };

/**
 * Inline "generate QR codes" control on a commitment row, for a contribution
 * that arrived without any. Rendered only when the API says this viewer may
 * mint them (`can_generate_tracking`) — the real check is server-side.
 */
export function GenerateCommitmentTrackingButton({
  requestId,
  contributionId,
}: {
  requestId: string;
  contributionId: string;
}) {
  const { dict } = useI18n();
  const t = dict.requestItem;
  const router = useRouter();
  const action = generateCommitmentTrackingAction.bind(
    null,
    requestId,
    contributionId,
  );
  const [state, formAction, pending] = useActionState(
    async () => action(),
    initialState,
  );

  // Swap this button for the tracking link once the codes exist.
  useEffect(() => {
    if (state.success) {
      router.refresh();
    }
  }, [state, router]);

  return (
    <form action={formAction} className="flex flex-col gap-1">
      <p className="text-xs text-muted">{t.generateTrackingHint}</p>
      <div>
        <Button type="submit" size="sm" variant="secondary" isPending={pending}>
          {dict.tracking.generateButton}
        </Button>
      </div>
      {state.error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{state.error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
    </form>
  );
}
