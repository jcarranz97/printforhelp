"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useActionState, useState } from "react";

import {
  type ModerationState,
  submitRequestAction,
  unpublishRequestAction,
} from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { ModerationStatus } from "@/lib/requests.api";

const initialState: ModerationState = { error: null };

type Copy = { title: string; body: string; cta: string | null };

/**
 * The author's view of where their campaign stands in the moderation pipeline.
 *
 * Only rendered for people entitled to see an unpublished campaign (the server
 * 404s it for everyone else), and deliberately never names *who* reviews it —
 * the author only needs to know it is waiting for approval.
 *
 * On a published campaign this collapses to the "hide and send back for review"
 * escape hatch, so a live campaign that turns out to be wrong can be pulled
 * down immediately rather than waiting on anyone.
 */
export function ModerationBanner({
  requestId,
  status,
  reviewNote,
  canManage,
}: {
  requestId: string;
  status: ModerationStatus;
  reviewNote: string | null;
  /** Whether the viewer may act on it (effective requester or maintainer). */
  canManage: boolean;
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
            <TextField name="note">
              <Label className="text-xs">{t.unpublishReason}</Label>
              <Input placeholder={t.noteplaceholder} />
            </TextField>
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
        {reviewNote && (
          <div
            className="rounded-lg border px-3 py-2"
            style={{ borderColor: "var(--card-border)" }}
          >
            <p className="text-xs font-semibold">{t.noteLabel}</p>
            <p className="mt-1 text-sm whitespace-pre-wrap">{reviewNote}</p>
          </div>
        )}
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
      </Alert.Content>
    </Alert>
  );
}
