"use client";

import { Button } from "@heroui/react";
import Link from "next/link";
import { useState } from "react";

import { confirmUnsubscribeAction } from "@/actions/notification-prefs.action";
import { useI18n } from "@/i18n/provider";

type UnsubscribeConfirmProps = {
  token: string;
  /** What the token will do, resolved server-side; null if the link is bad. */
  description: string | null;
};

/**
 * The no-login unsubscribe confirmation. The action is applied only on an
 * explicit "Confirm" click (a POST) so inbox link-scanners that prefetch the
 * URL cannot silently unsubscribe the user.
 */
export function UnsubscribeConfirm({
  token,
  description,
}: UnsubscribeConfirmProps) {
  const { dict } = useI18n();
  const t = dict.notifications.unsubscribe;
  const [state, setState] = useState<"idle" | "applying" | "done">("idle");
  const [message, setMessage] = useState<string | null>(null);

  if (description === null) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-danger">{t.invalid}</p>
        <ManageLink label={t.manage} />
      </div>
    );
  }

  if (state === "done") {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-lg font-medium">{t.done}</p>
        {message && <p className="text-sm text-muted">{message}</p>}
        <ManageLink label={t.manage} />
      </div>
    );
  }

  async function confirm() {
    setState("applying");
    const result = await confirmUnsubscribeAction(token);
    setMessage(result);
    setState("done");
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">{t.confirmHint}</p>
      <p className="text-sm font-medium">{description}</p>
      <Button isPending={state === "applying"} onPress={() => void confirm()}>
        {state === "applying" ? t.applying : t.confirm}
      </Button>
      <ManageLink label={t.manage} />
    </div>
  );
}

function ManageLink({ label }: { label: string }) {
  return (
    <Link
      href="/settings/notifications"
      className="text-sm text-[color:var(--accent-strong)] hover:underline"
    >
      {label}
    </Link>
  );
}
