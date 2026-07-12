"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import Link from "next/link";
import { useState, useTransition } from "react";

import {
  approveRequestAction,
  rejectRequestAction,
  requestChangesAction,
} from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { RequestListEntry } from "@/lib/requests.api";

type NotePrompt = "changes" | "reject" | null;

/**
 * The moderation queue: campaigns the community submitted, waiting for a
 * verdict. Approving publishes immediately; the other two verdicts take a note
 * that is shown back to the author (required when asking for more information,
 * optional but urged when rejecting).
 */
export function RequestQueue({ requests }: { requests: RequestListEntry[] }) {
  const { dict } = useI18n();
  const t = dict.moderation;

  if (requests.length === 0) {
    return (
      <Card variant="transparent" className="py-12 text-center">
        <Card.Content>
          <p className="text-muted">{t.queueEmpty}</p>
        </Card.Content>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {requests.map((request) => (
        <QueueRow key={request.id} request={request} />
      ))}
    </div>
  );
}

function QueueRow({ request }: { request: RequestListEntry }) {
  const { dict, locale } = useI18n();
  const t = dict.moderation;
  const [prompt, setPrompt] = useState<NotePrompt>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function run(action: () => Promise<{ error: string | null }>) {
    setError(null);
    startTransition(async () => {
      const result = await action();
      if (result.error) {
        setError(result.error);
        return;
      }
      setPrompt(null);
      setNote("");
    });
  }

  function submitNote() {
    const data = new FormData();
    data.set("note", note);
    run(() =>
      prompt === "changes"
        ? requestChangesAction(request.id, { error: null }, data)
        : rejectRequestAction(request.id, { error: null }, data),
    );
  }

  const submitted = request.submitted_at
    ? new Date(request.submitted_at).toLocaleDateString(
        locale === "es" ? "es-ES" : "en-US",
        { day: "numeric", month: "short", year: "numeric" },
      )
    : null;

  return (
    <Card>
      <Card.Content className="flex flex-col gap-3 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Link
              href={`/requests/${request.id}`}
              className="font-medium hover:underline"
            >
              {request.title}
            </Link>
            {request.beneficiary && (
              <p className="truncate text-xs text-muted">
                {request.beneficiary}
              </p>
            )}
            {submitted && (
              <p className="text-xs text-muted">
                {t.queueSubmittedAt}: {submitted}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              isPending={isPending && prompt === null}
              onPress={() => run(() => approveRequestAction(request.id))}
            >
              {t.approve}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onPress={() => setPrompt("changes")}
            >
              {t.requestChanges}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onPress={() => setPrompt("reject")}
            >
              {t.reject}
            </Button>
          </div>
        </div>

        {prompt !== null && (
          <div className="flex flex-col gap-2">
            <TextField value={note} onChange={setNote}>
              <Label className="text-xs">{t.noteLabel}</Label>
              <Input
                placeholder={
                  prompt === "changes"
                    ? t.notePlaceholderRequired
                    : t.noteplaceholder
                }
              />
            </TextField>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                isPending={isPending}
                onPress={submitNote}
              >
                {t.confirm}
              </Button>
              <button
                type="button"
                onClick={() => {
                  setPrompt(null);
                  setNote("");
                  setError(null);
                }}
                className="text-xs text-muted hover:underline"
              >
                {t.cancel}
              </button>
            </div>
          </div>
        )}

        {error && (
          <Alert status="danger">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </Card.Content>
    </Card>
  );
}
