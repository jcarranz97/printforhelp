"use client";

import { Alert, Button, Tooltip } from "@heroui/react";
import { useState, useTransition } from "react";

import {
  deleteContributorMessageAction,
  saveContributorMessageAction,
} from "@/actions/tracking.action";
import { useI18n } from "@/i18n/provider";
import type { ContributorMessage, QrBundleScope } from "@/lib/tracking.api";

// Keep in sync with the backend MAX_CONTRIBUTOR_MESSAGE_LENGTH; the textarea's
// maxLength blocks typing past it, and the counter shows how much is left.
const MESSAGE_MAX_LENGTH = 100;
const CHIP_PREVIEW_LENGTH = 42;

type BundleFormat = "pdf" | "png";

/**
 * The bundle download runs in two visibly distinct phases, and the maker needs
 * to be told them apart: the backend spends seconds *rendering* before it
 * sends a single byte (a 200-unit PDF is ~20 MB of rasterised pages), and only
 * then does the transfer start. "preparing" covers the silent render;
 * "downloading" carries real byte progress once the stream opens.
 */
type DownloadState =
  | { phase: "idle" }
  | { phase: "preparing"; format: BundleFormat }
  | {
      phase: "downloading";
      format: BundleFormat;
      received: number;
      total: number | null;
    }
  | { phase: "done" }
  | { phase: "failed" };

/** Minimum gap between progress repaints, in ms. */
const PROGRESS_PAINT_MS = 100;

const MIME: Record<BundleFormat, string> = {
  pdf: "application/pdf",
  png: "image/png",
};

function formatMb(bytes: number): string {
  return (bytes / 1_000_000).toFixed(1);
}

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
  const [download, setDownload] = useState<DownloadState>({ phase: "idle" });
  // Which QRs to print: both the single group QR and every per-unit QR (the
  // default), only the group QR (bag it all under one label), or only the
  // per-unit QRs.
  const [scope, setScope] = useState<QrBundleScope>("both");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function href(format: "pdf" | "png"): string {
    const params = new URLSearchParams({ format });
    if (scope !== "both") {
      params.set("scope", scope);
    }
    // Labels are always included when the part has one — makers consistently
    // want them in the shipment, so there is no opt-out.
    if (hasLabel) {
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

  const isDownloading =
    download.phase === "preparing" || download.phase === "downloading";

  /**
   * Fetch the bundle in the page rather than letting the browser navigate to
   * it, so the render wait and the transfer can be shown. The blob is handed
   * to a synthetic anchor at the end, which is what actually saves the file.
   */
  async function startDownload(format: BundleFormat) {
    if (isDownloading) {
      return;
    }
    setDownload({ phase: "preparing", format });
    let objectUrl: string | null = null;
    try {
      // Same-origin, so the httpOnly auth cookie rides along on its own.
      const res = await fetch(href(format));
      if (!res.ok || res.body === null) {
        throw new Error(`bundle request failed: ${res.status}`);
      }
      // Forwarded by the proxy route; without it we still stream, just with an
      // indeterminate bar instead of a percentage.
      const header = res.headers.get("content-length");
      const total = header ? Number(header) : null;

      const reader = res.body.getReader();
      const chunks: Uint8Array[] = [];
      let received = 0;
      setDownload({ phase: "downloading", format, received, total });

      // Repaint on a ~10fps tick rather than once per chunk: a slow connection
      // delivers a 20 MB bundle in far more (and far smaller) chunks than a
      // fast one, and setState per chunk would put a re-render of this whole
      // subtree between every read.
      let lastPaint = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        chunks.push(value);
        received += value.length;
        const now = performance.now();
        if (now - lastPaint >= PROGRESS_PAINT_MS) {
          lastPaint = now;
          setDownload({ phase: "downloading", format, received, total });
        }
      }

      objectUrl = URL.createObjectURL(
        new Blob(chunks as BlobPart[], { type: MIME[format] }),
      );
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `tracking-${groupId}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setDownload({ phase: "done" });
    } catch {
      setDownload({ phase: "failed" });
    } finally {
      // Revoking immediately can race the browser's read of the blob, so give
      // it a grace period before releasing the memory.
      if (objectUrl !== null) {
        const url = objectUrl;
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      }
    }
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

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">{t.scopeLabel}</legend>
        <p className="text-xs text-muted">{t.scopeHint}</p>
        <div className="flex flex-col gap-2">
          {(
            [
              {
                value: "both",
                label: t.scopeBothLabel,
                description: t.scopeBothHint,
              },
              {
                value: "group",
                label: t.scopeGroupLabel,
                description: t.scopeGroupHint,
              },
              {
                value: "individual",
                label: t.scopeIndividualLabel,
                description: t.scopeIndividualHint,
              },
            ] satisfies {
              value: QrBundleScope;
              label: string;
              description: string;
            }[]
          ).map((opt) => (
            <label
              key={opt.value}
              className="flex cursor-pointer items-start gap-2 rounded-lg border border-[var(--card-border)] px-3 py-2 text-sm has-[:checked]:border-[var(--accent-strong)] has-[:checked]:bg-default-50"
            >
              <input
                type="radio"
                name="qr_bundle_scope"
                value={opt.value}
                checked={scope === opt.value}
                onChange={() => setScope(opt.value)}
                className="mt-0.5 h-4 w-4"
              />
              <span className="flex flex-col">
                <span className="font-medium">{opt.label}</span>
                <span className="text-xs text-muted">{opt.description}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {/*
       * Buttons, never next/link: the App Router would intercept a <Link>
       * click, fetch the URL as an RSC payload, discard the (multi-MB) PDF it
       * gets back, and then hard-navigate — rendering and downloading the
       * bundle twice with no indicator in between. Fetching it ourselves keeps
       * it to one request *and* lets us show the progress below.
       */}
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={isDownloading}
          onClick={() => void startDownload("pdf")}
          className="rounded-lg bg-[var(--accent-strong)] px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {hasLabel ? t.downloadPdfWithLabels : t.downloadPdf}
        </button>
        <button
          type="button"
          disabled={isDownloading}
          onClick={() => void startDownload("png")}
          className="rounded-lg border border-[var(--card-border)] px-4 py-2 text-sm font-medium disabled:opacity-60"
        >
          {hasLabel ? t.downloadPngWithLabels : t.downloadPng}
        </button>
      </div>

      <DownloadStatus state={download} t={t} />
    </div>
  );
}

/**
 * Live feedback for the bundle download: an indeterminate spinner while the
 * backend renders (it sends nothing until the whole file is built), then a
 * real progress bar once bytes arrive, then a terminal success/error line.
 */
function DownloadStatus({
  state,
  t,
}: {
  state: DownloadState;
  t: ReturnType<typeof useI18n>["dict"]["tracking"];
}) {
  if (state.phase === "idle") {
    return null;
  }

  if (state.phase === "failed") {
    return (
      <Alert status="danger">
        <Alert.Indicator />
        <Alert.Content>
          <Alert.Description>{t.downloadFailed}</Alert.Description>
        </Alert.Content>
      </Alert>
    );
  }

  if (state.phase === "done") {
    return (
      <Alert status="success">
        <Alert.Indicator />
        <Alert.Content>
          <Alert.Description>{t.downloadReady}</Alert.Description>
        </Alert.Content>
      </Alert>
    );
  }

  const percent =
    state.phase === "downloading" && state.total !== null && state.total > 0
      ? Math.min(100, Math.round((state.received / state.total) * 100))
      : null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col gap-2 rounded-lg border border-[var(--card-border)] bg-default-50 px-3 py-2.5"
    >
      <div className="flex items-center gap-2 text-sm">
        <Spinner />
        <span className="font-medium">
          {state.phase === "preparing"
            ? t.downloadPreparing
            : t.downloadProgress}
        </span>
        {state.phase === "downloading" && (
          <span className="ml-auto text-xs text-muted tabular-nums">
            {percent !== null
              ? `${percent}%`
              : `${formatMb(state.received)} MB`}
          </span>
        )}
      </div>

      {/* Indeterminate while rendering (no total to count against yet). */}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-default-200">
        <div
          className={
            percent !== null
              ? "h-full rounded-full bg-[var(--accent-strong)] transition-[width] duration-150"
              : "h-full w-1/3 animate-pulse rounded-full bg-[var(--accent-strong)]"
          }
          style={percent !== null ? { width: `${percent}%` } : undefined}
        />
      </div>

      {state.phase === "preparing" && (
        <p className="text-xs text-muted">{t.downloadPreparingHint}</p>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="size-4 shrink-0 animate-spin text-[var(--accent-strong)]"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
        className="opacity-25"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}
