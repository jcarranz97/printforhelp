"use client";

import { Checkbox } from "@heroui/react";
import { useState } from "react";

import { updatePreferenceAction } from "@/actions/notification-prefs.action";
import { useI18n } from "@/i18n/provider";
import type {
  NotificationCategory,
  NotificationPreference,
} from "@/lib/notification-prefs.api";

type Channel = "in_app_enabled" | "email_enabled";

type PreferencesFormProps = {
  initial: NotificationPreference[];
};

/**
 * The Jira-style preference matrix: one row per notification category with
 * an in-app and an email checkbox. Toggling a box saves optimistically and
 * reverts if the request fails.
 */
export function PreferencesForm({ initial }: PreferencesFormProps) {
  const { dict } = useI18n();
  const t = dict.notifications.preferences;
  const [prefs, setPrefs] = useState<NotificationPreference[]>(initial);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const categoryCopy = t.categories as Record<
    string,
    { label: string; description: string }
  >;

  async function toggle(
    category: NotificationCategory,
    channel: Channel,
    value: boolean,
  ) {
    const previous = prefs;
    const next = prefs.map((p) =>
      p.category === category ? { ...p, [channel]: value } : p,
    );
    setPrefs(next);
    setStatus("idle");
    const updated = next.find((p) => p.category === category)!;
    const result = await updatePreferenceAction(category, {
      in_app_enabled: updated.in_app_enabled,
      email_enabled: updated.email_enabled,
    });
    if (result === null) {
      setPrefs(previous);
      setStatus("error");
    } else {
      setStatus("saved");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto">
        <div className="min-w-[420px]">
          <div className="grid grid-cols-[1fr_5rem_5rem] items-center gap-2 border-b border-default-200 pb-2 text-xs font-semibold uppercase text-muted">
            <span>{t.columnEvent}</span>
            <span className="text-center">{t.columnInApp}</span>
            <span className="text-center">{t.columnEmail}</span>
          </div>
          {prefs.map((pref) => {
            const copy = categoryCopy[pref.category];
            return (
              <div
                key={pref.category}
                className="grid grid-cols-[1fr_5rem_5rem] items-center gap-2 border-b border-default-100 py-3"
              >
                <div className="flex flex-col">
                  <span className="text-sm font-medium">{copy.label}</span>
                  <span className="text-xs text-muted">{copy.description}</span>
                </div>
                <div className="flex justify-center">
                  <Checkbox
                    isSelected={pref.in_app_enabled}
                    onChange={(v) =>
                      void toggle(pref.category, "in_app_enabled", v)
                    }
                    aria-label={`${copy.label} — ${t.columnInApp}`}
                  >
                    <Checkbox.Content>
                      <Checkbox.Control>
                        <Checkbox.Indicator />
                      </Checkbox.Control>
                    </Checkbox.Content>
                  </Checkbox>
                </div>
                <div className="flex justify-center">
                  <Checkbox
                    isSelected={pref.email_enabled}
                    onChange={(v) =>
                      void toggle(pref.category, "email_enabled", v)
                    }
                    aria-label={`${copy.label} — ${t.columnEmail}`}
                  >
                    <Checkbox.Content>
                      <Checkbox.Control>
                        <Checkbox.Indicator />
                      </Checkbox.Control>
                    </Checkbox.Content>
                  </Checkbox>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <p
        aria-live="polite"
        className={`text-sm ${
          status === "error" ? "text-danger" : "text-muted"
        }`}
      >
        {status === "saved" ? t.saved : status === "error" ? t.error : " "}
      </p>
    </div>
  );
}
