"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useActionState, useEffect } from "react";

import {
  type TrackingState,
  generateTrackingAction,
} from "@/actions/tracking.action";
import { useI18n } from "@/i18n/provider";

const initialState: TrackingState = { error: null };

/** Prompt + button to generate tracking for a Contribution that has none. */
export function GenerateTrackingButton({
  contributionId,
}: {
  contributionId: string;
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const router = useRouter();
  const action = generateTrackingAction.bind(null, contributionId);
  const [state, formAction, pending] = useActionState(
    async () => action(),
    initialState,
  );

  // Swap the "generate" prompt for the full tracking view once created.
  useEffect(() => {
    if (state.success) {
      router.refresh();
    }
  }, [state, router]);

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">{t.generateTitle}</h2>
        <p className="text-sm text-muted">{t.generateDescription}</p>
      </div>
      <div>
        <Button type="submit" variant="primary" isPending={pending}>
          {t.generateButton}
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
