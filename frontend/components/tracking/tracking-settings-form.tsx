"use client";

import { Alert, Button, type Key, ListBox, Select } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState } from "react";

import {
  type TrackingState,
  updateTrackingAction,
} from "@/actions/tracking.action";
import { MembersInput } from "@/components/tracking/members-input";
import { useI18n } from "@/i18n/provider";
import type { TrackingVisibility } from "@/lib/tracking.api";

const initialState: TrackingState = { error: null };

/** Owner control for visibility (private/group/public) and named members. */
export function TrackingSettingsForm({
  groupId,
  contributionId,
  visibility,
  members,
}: {
  groupId: string;
  contributionId: string;
  visibility: TrackingVisibility;
  members: string[];
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const router = useRouter();
  const action = updateTrackingAction.bind(null, groupId, contributionId);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [current, setCurrent] = useState<TrackingVisibility>(visibility);

  // Re-fetch the page's server components so sibling sections (the share
  // link, hints) reflect the just-saved visibility without a manual reload.
  useEffect(() => {
    if (state.success) {
      router.refresh();
    }
  }, [state, router]);

  // Follow the persisted value once the refresh delivers it, so the control
  // can never linger on a stale selection after a save.
  useEffect(() => {
    setCurrent(visibility);
  }, [visibility]);

  const labels: Record<TrackingVisibility, string> = {
    private: t.visibilityPrivate,
    group: t.visibilityGroup,
    public: t.visibilityPublic,
  };

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <input type="hidden" name="visibility" value={current} />
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">{t.visibilityLabel}</span>
        <div className="w-full sm:w-72">
          <Select
            aria-label={t.visibilityLabel}
            value={current}
            onChange={(value: Key | null) =>
              setCurrent((value ?? "private") as TrackingVisibility)
            }
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                {(["private", "group", "public"] as const).map((option) => (
                  <ListBox.Item
                    key={option}
                    id={option}
                    textValue={labels[option]}
                  >
                    {labels[option]}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
        <p className="text-xs text-muted">{t.visibilityHelp}</p>
      </div>

      {current === "group" && (
        <div className="flex flex-col gap-1.5">
          <MembersInput
            name="members"
            label={t.membersLabel}
            defaultMembers={members}
          />
          <p className="text-xs text-muted">{t.membersHelp}</p>
        </div>
      )}
      {/* Keep members in the payload even when the input is hidden, so the
          saved list is preserved if the owner toggles away and back. */}
      {current !== "group" && (
        <input type="hidden" name="members" value={members.join(",")} />
      )}

      <div>
        <Button type="submit" variant="secondary" isPending={pending}>
          {t.saveSettings}
        </Button>
      </div>

      {state.success && (
        <Alert status="success">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{t.settingsSaved}</Alert.Description>
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
