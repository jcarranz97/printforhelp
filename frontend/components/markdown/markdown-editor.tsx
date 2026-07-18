"use client";

import { Alert, Kbd } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { MdImage } from "react-icons/md";

import { searchUsersAction } from "@/actions/notifications.action";
import { uploadMarkdownImageAction } from "@/actions/uploads.action";
import { Markdown } from "@/components/comments/markdown";
import { useI18n } from "@/i18n/provider";
import type { UserSearchResult } from "@/lib/users.api";

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
  /** Show the "paste/drag an image" hint under the editor. Off for fields
   * (e.g. the project description) that shouldn't advertise image uploads. */
  showImageHint?: boolean;
  /**
   * When set, pressing Enter (without Shift, and while the @mention menu is
   * closed) submits by calling this. Shift+Enter still inserts a newline. This
   * is opt-in so only the comment composer/edit form get chat-style Enter to
   * send — other fields (e.g. descriptions) keep Enter = newline. A
   * "Shift+Enter for a new line" hint is shown when this is provided.
   */
  onSubmit?: () => void;
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
  showImageHint = true,
  onSubmit,
}: MarkdownEditorProps) {
  const { dict } = useI18n();
  const t = dict.markdownEditor;
  const tm = dict.mentions;

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

  // @mention autocomplete state. `mentionQuery === null` means closed;
  // `mentionStart` is the index of the triggering `@` in the text.
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionStart, setMentionStart] = useState(-1);
  const [suggestions, setSuggestions] = useState<UserSearchResult[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [mentionLoading, setMentionLoading] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function onPickFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    // Reset so picking the same file again still fires onChange.
    e.target.value = "";
    if (files.length > 0) {
      void uploadFiles(files);
    }
  }

  function closeMention() {
    setMentionQuery(null);
    setMentionStart(-1);
    setSuggestions([]);
    setActiveIndex(0);
  }

  // Detect an `@token` immediately before the caret and open the typeahead.
  function detectMention() {
    const el = textareaRef.current;
    if (!el) {
      return;
    }
    const caret = el.selectionStart ?? 0;
    const before = el.value.slice(0, caret);
    const match = /(?:^|\s)@([A-Za-z0-9_.-]*)$/.exec(before);
    if (!match) {
      closeMention();
      return;
    }
    const query = match[1];
    setMentionStart(caret - query.length - 1);
    setMentionQuery(query);
  }

  // Debounced search whenever the mention query changes. An empty query
  // still searches so the menu shows suggestions the instant `@` is typed.
  useEffect(() => {
    if (mentionQuery === null) {
      return;
    }
    let cancelled = false;
    setMentionLoading(true);
    const id = setTimeout(async () => {
      const users = await searchUsersAction(mentionQuery);
      if (!cancelled) {
        setSuggestions(users);
        setActiveIndex(0);
        setMentionLoading(false);
      }
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [mentionQuery]);

  function applyMention(user: UserSearchResult) {
    const el = textareaRef.current;
    const current = latestRef.current;
    if (!el || mentionStart < 0) {
      closeMention();
      return;
    }
    const caret = el.selectionStart ?? current.length;
    const insertion = `@${user.username} `;
    const next = `${current.slice(0, mentionStart)}${insertion}${current.slice(caret)}`;
    setText(next);
    closeMention();
    const nextCaret = mentionStart + insertion.length;
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(nextCaret, nextCaret);
    });
  }

  function onTextareaKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // While the @mention menu is open, keys drive the menu — never submit.
    if (mentionQuery !== null && suggestions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % suggestions.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex(
          (i) => (i - 1 + suggestions.length) % suggestions.length,
        );
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        applyMention(suggestions[activeIndex]);
      } else if (e.key === "Escape") {
        e.preventDefault();
        closeMention();
      }
      return;
    }
    // Chat-style submit (opt-in via `onSubmit`): plain Enter sends, Shift+Enter
    // inserts a newline. `isComposing` skips IME/dead-key composition (e.g.
    // accented characters) so a mid-composition Enter doesn't submit.
    if (
      onSubmit &&
      e.key === "Enter" &&
      !e.shiftKey &&
      !e.nativeEvent.isComposing
    ) {
      e.preventDefault();
      onSubmit();
    }
  }

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
      <div className="flex items-center border-b border-default-200">
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
        {tab === "write" && showImageHint && (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isDisabled}
            className="ml-auto flex items-center gap-1 px-2 py-1.5 text-sm text-muted hover:text-foreground disabled:opacity-50"
          >
            <MdImage aria-hidden className="text-base" />
            {t.attach}
          </button>
        )}
        {/* Native picker: on mobile this offers camera + photo library and
            transcodes iPhone HEIC photos to JPEG for the file input. */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={onPickFiles}
        />
      </div>

      {tab === "write" ? (
        <div className="relative">
          <textarea
            ref={textareaRef}
            rows={rows}
            placeholder={placeholder}
            aria-label={ariaLabel ?? placeholder}
            value={text}
            disabled={isDisabled}
            onChange={(e) => {
              setText(e.target.value);
              detectMention();
            }}
            onClick={detectMention}
            onKeyUp={(e) => {
              // Caret moves that aren't handled by the mention key handler.
              if (
                !["ArrowDown", "ArrowUp", "Enter", "Tab", "Escape"].includes(
                  e.key,
                )
              ) {
                detectMention();
              }
            }}
            onKeyDown={onTextareaKeyDown}
            onBlur={closeMention}
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
          {mentionQuery !== null && (
            <div className="absolute inset-x-0 top-full z-20 mt-1 max-h-56 overflow-y-auto rounded-lg border border-default-300 bg-[var(--background)] shadow-lg">
              {mentionLoading && suggestions.length === 0 ? (
                <p className="px-3 py-2 text-sm text-muted">{tm.loading}</p>
              ) : suggestions.length === 0 ? (
                <p className="px-3 py-2 text-sm text-muted">{tm.empty}</p>
              ) : (
                <ul>
                  {suggestions.map((u, i) => (
                    <li key={u.id}>
                      <button
                        type="button"
                        // mousedown (not click) so the textarea keeps focus.
                        onMouseDown={(e) => {
                          e.preventDefault();
                          applyMention(u);
                        }}
                        onMouseEnter={() => setActiveIndex(i)}
                        className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm ${
                          i === activeIndex ? "bg-default-100" : ""
                        }`}
                      >
                        <span className="font-medium">@{u.username}</span>
                        {u.full_name && (
                          <span className="truncate text-muted">
                            {u.full_name}
                          </span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
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

      {(uploading > 0 || showImageHint || onSubmit) && (
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-muted">
            {uploading > 0
              ? t.uploadingHint
              : showImageHint
                ? t.attachHint
                : ""}
          </span>
          {onSubmit && (
            <span className="flex shrink-0 items-center gap-1.5 text-xs text-muted">
              <Kbd>
                <Kbd.Abbr keyValue="shift" />
                <Kbd.Abbr keyValue="enter" />
              </Kbd>
              {t.newlineHint}
            </span>
          )}
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
    </div>
  );
}
