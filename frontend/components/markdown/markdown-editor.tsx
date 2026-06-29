"use client";

import { Alert } from "@heroui/react";
import { useRef, useState } from "react";

import { uploadMarkdownImageAction } from "@/actions/uploads.action";
import { Markdown } from "@/components/comments/markdown";
import { useI18n } from "@/i18n/provider";

type MarkdownEditorProps = {
  /** Form field name — set this to submit the value inside a `<form>`. */
  name?: string;
  /** Controlled value (pair with `onChange`). */
  value?: string;
  onChange?: (value: string) => void;
  /** Initial value for uncontrolled (form) usage. */
  defaultValue?: string;
  placeholder?: string;
  rows?: number;
  ariaLabel?: string;
  isDisabled?: boolean;
};

const IMAGE_TYPE = /^image\//;

/**
 * GitHub-style Markdown editor with Write/Preview tabs and inline image
 * uploads. Pasting, dropping, or picking an image uploads it via
 * `uploadMarkdownImageAction` and inserts `![name](url)` at the caret
 * (a placeholder marker is shown while the upload is in flight).
 *
 * Works both controlled (`value` + `onChange`, e.g. the comment composer)
 * and as a plain form field (`name` + `defaultValue`, e.g. description
 * fields). When `name` is set the current text is mirrored into a hidden
 * input so it submits even while the Preview tab is showing.
 */
export function MarkdownEditor({
  name,
  value,
  onChange,
  defaultValue = "",
  placeholder,
  rows = 5,
  ariaLabel,
  isDisabled,
}: MarkdownEditorProps) {
  const { dict } = useI18n();
  const t = dict.markdownEditor;

  const isControlled = value !== undefined;
  const [internal, setInternal] = useState(defaultValue);
  const text = isControlled ? value : internal;

  // Mirror of the latest text so async upload callbacks can do string
  // replacement without stale closures (works in controlled mode too).
  const latestRef = useRef(text);
  latestRef.current = text;

  const [tab, setTab] = useState<"write" | "preview">("write");
  const [uploading, setUploading] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function setText(next: string) {
    latestRef.current = next;
    if (!isControlled) {
      setInternal(next);
    }
    onChange?.(next);
  }

  function errorMessage(code: string): string {
    return t.errors[code as keyof typeof t.errors] ?? t.errors.default;
  }

  function insertAtCaret(snippet: string) {
    const el = textareaRef.current;
    const current = latestRef.current;
    if (!el) {
      setText(current ? `${current}\n${snippet}\n` : `${snippet}\n`);
      return;
    }
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const prefix = current.slice(0, start);
    const suffix = current.slice(end);
    // Keep image markers on their own line so they render cleanly.
    const lead = prefix && !prefix.endsWith("\n") ? "\n" : "";
    const tail = suffix === "" || suffix.startsWith("\n") ? "" : "\n";
    setText(`${prefix}${lead}${snippet}${tail}${suffix}`);
  }

  async function uploadFiles(files: File[]) {
    const images = files.filter((f) => IMAGE_TYPE.test(f.type));
    if (images.length === 0) {
      return;
    }
    setError(null);
    for (const file of images) {
      const marker = `![${t.uploading} ${file.name}](uploading-${crypto.randomUUID()})`;
      insertAtCaret(marker);
      setUploading((n) => n + 1);
      const fd = new FormData();
      fd.append("file", file);
      try {
        const res = await uploadMarkdownImageAction(fd);
        if ("url" in res) {
          setText(
            latestRef.current.replace(marker, `![${file.name}](${res.url})`),
          );
        } else {
          setText(latestRef.current.replace(marker, ""));
          setError(errorMessage(res.errorCode));
        }
      } catch {
        setText(latestRef.current.replace(marker, ""));
        setError(errorMessage("default"));
      } finally {
        setUploading((n) => n - 1);
      }
    }
  }

  const tabClass = (active: boolean) =>
    `px-3 py-1.5 text-sm font-medium border-b-2 -mb-px ${
      active
        ? "border-primary text-foreground"
        : "border-transparent text-muted hover:text-foreground"
    }`;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between border-b border-default-200">
        <div className="flex">
          <button
            type="button"
            className={tabClass(tab === "write")}
            onClick={() => setTab("write")}
          >
            {t.write}
          </button>
          <button
            type="button"
            className={tabClass(tab === "preview")}
            onClick={() => setTab("preview")}
          >
            {t.preview}
          </button>
        </div>
        {tab === "write" && (
          <button
            type="button"
            className="text-xs font-medium text-muted hover:text-foreground"
            onClick={() => fileInputRef.current?.click()}
            disabled={isDisabled}
          >
            {t.attach}
          </button>
        )}
      </div>

      {tab === "write" ? (
        <textarea
          ref={textareaRef}
          rows={rows}
          placeholder={placeholder}
          aria-label={ariaLabel ?? placeholder}
          value={text}
          disabled={isDisabled}
          onChange={(e) => setText(e.target.value)}
          onPaste={(e) => {
            const files = Array.from(e.clipboardData.files);
            if (files.some((f) => IMAGE_TYPE.test(f.type))) {
              e.preventDefault();
              void uploadFiles(files);
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            const files = Array.from(e.dataTransfer.files);
            if (files.some((f) => IMAGE_TYPE.test(f.type))) {
              e.preventDefault();
              setDragging(false);
              void uploadFiles(files);
            }
          }}
          className={`min-h-28 w-full resize-y rounded-lg border bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary ${
            dragging ? "border-dashed border-primary" : "border-default-300"
          }`}
        />
      ) : (
        <div className="min-h-28 rounded-lg border border-default-300 px-3 py-2">
          {text.trim() ? (
            <Markdown source={text} />
          ) : (
            <p className="text-sm text-muted">{t.previewEmpty}</p>
          )}
        </div>
      )}

      {name && <input type="hidden" name={name} value={text} />}

      <span className="text-xs text-muted">
        {uploading > 0 ? t.uploadingHint : t.attachHint}
      </span>

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        multiple
        hidden
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          void uploadFiles(files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
