"use client";

import { Label } from "@heroui/react";

import { UsernameField } from "@/components/settings/username-field";
import { useI18n } from "@/i18n/provider";
import type { CurrentUser } from "@/lib/auth.api";

/**
 * The "Account" tab — the fields that identify the account rather than
 * describe the person: the handle and the email it is reachable at.
 *
 * There is no form button here. The username saves itself (rate-limited,
 * behind its own confirmation) and the email is read-only for now, so a
 * single "save" would have nothing left to own.
 */
export function AccountForm({ user }: { user: CurrentUser }) {
  const { dict } = useI18n();
  const t = dict.settingsProfile;

  return (
    <div className="flex flex-col gap-5">
      <UsernameField user={user} />

      <div className="flex flex-col gap-1.5">
        <Label>{t.emailLabel}</Label>
        <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-default-100 px-3 py-2">
          <span className="truncate text-sm text-foreground/80">
            {user.email ?? t.noEmail}
          </span>
          <span className="shrink-0 rounded-full bg-default-200 px-2 py-0.5 text-xs font-medium text-muted">
            {t.emailReadOnly}
          </span>
        </div>
        <p className="text-xs text-muted">{t.emailHint}</p>
      </div>
    </div>
  );
}
