"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useRef } from "react";

import { TagInput } from "@/components/forms/tag-input";
import { type TrackingState, addRecordAction } from "@/actions/tracking.action";
import { useI18n } from "@/i18n/provider";

const initialState: TrackingState = { error: null };

/** The "add an update" form on a public tracking page. Open to anyone who
 * can view the token; guests post anonymously, members can opt to. */
export function AddRecordForm({
  trackingToken,
  isLoggedIn,
  suggestions,
}: {
  trackingToken: string;
  isLoggedIn: boolean;
  suggestions: string[];
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const router = useRouter();
  const action = addRecordAction.bind(null, trackingToken);
  const [state, formAction, pending] = useActionState(action, initialState);
  const formRef = useRef<HTMLFormElement>(null);

  // Clear the form and re-fetch the timeline so the new update shows at once.
  useEffect(() => {
    if (state.success) {
      formRef.current?.reset();
      router.refresh();
    }
  }, [state, router]);

  return (
    <form ref={formRef} action={formAction} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="description" className="text-sm font-medium">
          {t.descriptionLabel}
        </label>
        <textarea
          id="description"
          name="description"
          required
          rows={3}
          placeholder={t.descriptionPlaceholder}
          className="rounded-lg border border-[var(--card-border)] bg-transparent px-3 py-2 text-sm outline-none"
        />
      </div>

      <TagInput name="tags" label={t.tagsLabel} suggestions={suggestions} />

      {isLoggedIn ? (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="display_anonymous" className="h-4 w-4" />
          {t.postAnonymously}
        </label>
      ) : (
        <p className="text-xs text-muted">{t.guestNote}</p>
      )}

      <div>
        <Button type="submit" variant="primary" isPending={pending}>
          {t.submitUpdate}
        </Button>
      </div>

      {state.success && (
        <Alert status="success">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{t.updatePosted}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
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
