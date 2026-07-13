"use client";

import { Alert, Button } from "@heroui/react";
import { useActionState, useState, useTransition } from "react";

import {
  approveRequestAction,
  type ModerationState,
  rejectRequestAction,
  submitRequestAction,
  unpublishRequestAction,
} from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { ModerationStatus } from "@/lib/requests.api";

const initialState: ModerationState = { error: null };

type Copy = { title: string; body: string; cta: string | null };

/**
 * The author's view of where their campaign stands in the moderation pipeline,
 * and — for a maintainer/admin — the place they act on it.
 *
 * Only rendered for people entitled to see an unpublished campaign (the server
 * 404s it for everyone else), and deliberately never names *who* reviews it:
 * the author only needs to know it is waiting for approval.
 *
 * There is no "review feedback" text box. A one-shot note could not answer a
 * follow-up question, so the back-and-forth happens in the private review
 * thread rendered directly below this banner (a separate timeline from the
 * campaign's public comments, so publishing never exposes it). The verdict
 * buttons here just move the state; the reasoning lives in that thread.
 */
export function ModerationBanner({
  requestId,
  status,
  canManage,
  isMaintainer = false,
}: {
  requestId: string;
  status: ModerationStatus;
  /** Whether the viewer may act on it (effective requester or maintainer). */
  canManage: boolean;
  /** Maintainers/admins additionally get the approve/ask/reject controls. */
  isMaintainer?: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.moderation;
  const [submitState, submit, submitting] = useActionState(
    async () => submitRequestAction(requestId),
    initialState,
  );
  const [unpublishState, unpublish, unpublishing] = useActionState(
    unpublishRequestAction.bind(null, requestId),
    initialState,
  );
  const [unpublishOpen, setUnpublishOpen] = useState(false);

  if (status === "approved") {
    if (!canManage) {
      return null;
    }
    return (
      <div className="flex flex-col gap-2">
        {unpublishOpen ? (
          <form
            action={unpublish}
            className="flex flex-col gap-2 rounded-lg border px-3 py-3"
            style={{ borderColor: "var(--card-border)" }}
          >
            <p className="text-xs text-muted">{t.unpublishHint}</p>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="submit"
                size="sm"
                variant="secondary"
                isPending={unpublishing}
              >
                {t.confirm}
              </Button>
              <button
                type="button"
                onClick={() => setUnpublishOpen(false)}
                className="text-xs text-muted hover:underline"
              >
                {t.cancel}
              </button>
            </div>
            {unpublishState.error && (
              <Alert status="danger">
                <Alert.Indicator />
                <Alert.Content>
                  <Alert.Description>{unpublishState.error}</Alert.Description>
                </Alert.Content>
              </Alert>
            )}
          </form>
        ) : (
          <button
            type="button"
            onClick={() => setUnpublishOpen(true)}
            className="self-start text-xs text-muted hover:underline"
          >
            {t.unpublish}
          </button>
        )}
      </div>
    );
  }

  const copy: Record<Exclude<ModerationStatus, "approved">, Copy> = {
    draft: { title: t.draftTitle, body: t.draftBody, cta: t.submit },
    pending: { title: t.pendingTitle, body: t.pendingBody, cta: null },
    changes_requested: {
      title: t.changesTitle,
      body: t.changesBody,
      cta: t.resubmit,
    },
    rejected: { title: t.rejectedTitle, body: t.rejectedBody, cta: t.resubmit },
  };
  const { title, body, cta } = copy[status];
  const tone = status === "rejected" ? "danger" : "warning";

  return (
    <Alert status={tone}>
      <Alert.Indicator />
      <Alert.Content className="flex flex-col gap-2">
        <Alert.Title>{title}</Alert.Title>
        <Alert.Description>{body}</Alert.Description>

        {canManage && cta && (
          <form action={submit}>
            <Button type="submit" size="sm" isPending={submitting}>
              {cta}
            </Button>
          </form>
        )}
        {submitState.error && (
          <p className="text-sm text-danger">{submitState.error}</p>
        )}

        {isMaintainer && status === "pending" && (
          <ReviewActions requestId={requestId} />
        )}
      </Alert.Content>
    </Alert>
  );
}

/**
 * The reviewer's two decisions — approve, or reject — for a pending campaign.
 *
 * There is deliberately no third "ask for more information" button. Needing
 * more information is not a decision, it is a question: the reviewer asks it in
 * the private review thread below and the campaign simply stays `pending`,
 * where it belongs until they can actually decide. A separate status only
 * pushed the campaign out of the queue the reviewer was working through.
 */
function ReviewActions({ requestId }: { requestId: string }) {
  const { dict } = useI18n();
  const t = dict.moderation;
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function run(action: () => Promise<{ error: string | null }>) {
    setError(null);
    startTransition(async () => {
      const result = await action();
      if (result.error) {
        setError(result.error);
      }
    });
  }

  return (
    <div
      className="mt-2 flex flex-col gap-2 border-t pt-3"
      style={{ borderColor: "var(--card-border)" }}
    >
      <p className="text-xs font-semibold">{t.reviewHeading}</p>
      <p className="text-xs text-muted">{t.reviewHint}</p>
      <p className="text-xs text-muted">{t.reviewAskHint}</p>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          isPending={isPending}
          onPress={() => run(() => approveRequestAction(requestId))}
        >
          {t.approve}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          isPending={isPending}
          onPress={() => run(() => rejectRequestAction(requestId))}
        >
          {t.reject}
        </Button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
