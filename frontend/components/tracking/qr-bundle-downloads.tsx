"use client";

import { Alert, Button, Tooltip } from "@heroui/react";
import Link from "next/link";
import { useState, useTransition } from "react";

import {
  deleteContributorMessageAction,
  saveContributorMessageAction,
} from "@/actions/tracking.action";
import { useI18n } from "@/i18n/provider";
import type { ContributorMessage } from "@/lib/tracking.api";

// Keep in sync with the backend MAX_CONTRIBUTOR_MESSAGE_LENGTH; the textarea's
// maxLength blocks typing past it, and the counter shows how much is left.
const MESSAGE_MAX_LENGTH = 100;
const CHIP_PREVIEW_LENGTH = 42;

/**
 * QR-bundle download area: a contributor-message editor with reusable saved
 * messages ("templates") plus an optional "include label" toggle and the
 * PDF/PNG links.
 *
 * The message drives the download directly: text in the box is printed above
 * each QR, an empty box prints none. Saved messages (owned by the user, not
 * the tracking) are shown as chips to reuse anywhere; "Remember my message"
 * appends the current text to that list.
 */
export function QrBundleDownloads({
  groupId,
  hasLabel,
  savedMessages,
}: {
  groupId: string;
  hasLabel: boolean;
  savedMessages: ContributorMessage[];
}) {
  const { dict } = useI18n();
  const t = dict.tracking;

  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState(savedMessages);
  const [includeLabel, setIncludeLabel] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function href(format: "pdf" | "png"): string {
    const params = new URLSearchParams({ format });
    if (hasLabel && includeLabel) {
      params.set("labels", "1");
    }
    // A non-empty message is printed above each QR; empty means no message.
    const note = message.trim();
    if (note) {
      params.set("message", "1");
      params.set("message_text", note);
    }
    return `/tracking-bundle/${groupId}?${params.toString()}`;
  }

  function save() {
    startTransition(async () => {
      const res = await saveContributorMessageAction(message);
      setError(res.error);
      if (res.messages) {
        setMessages(res.messages);
      }
    });
  }

  function remove(id: string) {
    startTransition(async () => {
      const res = await deleteContributorMessageAction(id);
      setError(res.error);
      if (res.messages) {
        setMessages(res.messages);
      }
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="contributor_message" className="text-sm font-medium">
          {t.messageLabel}
        </label>

        {messages.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <p className="text-xs text-muted">{t.savedMessagesHint}</p>
            <div className="flex flex-wrap gap-2">
              {messages.map((m) => (
                <span
                  key={m.id}
                  className="inline-flex items-center gap-1 rounded-full border border-[var(--card-border)] bg-default-50 pl-3 pr-1 text-xs"
                >
                  <button
                    type="button"
                    title={m.body}
                    onClick={() => setMessage(m.body)}
                    className="py-1 text-left hover:text-foreground"
                  >
                    {m.body.length > CHIP_PREVIEW_LENGTH
                      ? `${m.body.slice(0, CHIP_PREVIEW_LENGTH)}…`
                      : m.body}
                  </button>
                  <button
                    type="button"
                    aria-label={t.deleteMessageAria}
                    onClick={() => remove(m.id)}
                    className="flex size-5 items-center justify-center rounded-full text-muted hover:bg-default-200 hover:text-danger"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}

        <textarea
          id="contributor_message"
          rows={3}
          maxLength={MESSAGE_MAX_LENGTH}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t.messagePlaceholder}
          className="rounded-lg border border-[var(--card-border)] bg-transparent px-3 py-2 text-sm outline-none"
        />
        <div className="flex items-start justify-between gap-3">
          <p className="text-xs text-muted">{t.messageHelp}</p>
          <p className="shrink-0 text-xs text-muted tabular-nums">
            {MESSAGE_MAX_LENGTH - message.length} {t.messageCharsLeft}
          </p>
        </div>
        <div>
          <Tooltip delay={300}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              isPending={isPending}
              isDisabled={!message.trim()}
              onPress={save}
            >
              {t.rememberMessage}
            </Button>
            <Tooltip.Content className="max-w-xs">
              <p>{t.rememberMessageTooltip}</p>
            </Tooltip.Content>
          </Tooltip>
        </div>
        {error && (
          <Alert status="danger">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </div>

      {hasLabel && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeLabel}
            onChange={(e) => setIncludeLabel(e.target.checked)}
            className="h-4 w-4"
          />
          {t.includeLabel}
        </label>
      )}

      <div className="flex flex-wrap gap-3">
        <Link
          href={href("pdf")}
          className="rounded-lg bg-[var(--accent-strong)] px-4 py-2 text-sm font-medium text-white"
          prefetch={false}
        >
          {t.downloadPdf}
        </Link>
        <Link
          href={href("png")}
          className="rounded-lg border border-[var(--card-border)] px-4 py-2 text-sm font-medium"
          prefetch={false}
        >
          {t.downloadPng}
        </Link>
      </div>
    </div>
  );
}
