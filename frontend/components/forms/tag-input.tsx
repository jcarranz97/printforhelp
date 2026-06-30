"use client";

import { Chip } from "@heroui/react";
import { useId, useMemo, useState } from "react";
import { MdClose } from "react-icons/md";

import { useI18n } from "@/i18n/provider";

/** Split raw input on commas into trimmed, non-empty tag tokens. */
function tokenize(raw: string): string[] {
  return raw
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

/**
 * A creatable, autocompleting tag input (GitHub/JIRA style). Renders the
 * selected tags as removable chips plus a text field that suggests existing
 * tags as you type and lets you create brand-new ones. The selected tags are
 * mirrored to a hidden `name` field (comma-separated) so it drops into any
 * form that already parses a comma-separated `tags` value server-side.
 */
export function TagInput({
  name,
  label,
  defaultTags = [],
  suggestions = [],
}: {
  name: string;
  label: string;
  defaultTags?: string[];
  suggestions?: string[];
}) {
  const { dict, locale } = useI18n();
  const t = dict.tagInput;
  const inputId = useId();
  const [selected, setSelected] = useState<string[]>(defaultTags);
  const [input, setInput] = useState("");
  const [open, setOpen] = useState(false);

  const sortedSuggestions = useMemo(
    () =>
      [...suggestions].sort((a, b) =>
        a.localeCompare(b, locale, { sensitivity: "base" }),
      ),
    [suggestions, locale],
  );

  function addTokens(raw: string) {
    const parts = tokenize(raw);
    if (parts.length === 0) {
      return;
    }
    setSelected((current) => {
      const next = [...current];
      for (const part of parts) {
        if (!next.some((s) => s.toLowerCase() === part.toLowerCase())) {
          next.push(part);
        }
      }
      return next;
    });
    setInput("");
  }

  function removeTag(tag: string) {
    setSelected((current) => current.filter((s) => s !== tag));
  }

  const query = input.trim().toLowerCase();
  // Existing tags not yet selected, matching what's being typed.
  const matches = sortedSuggestions.filter(
    (tag) =>
      !selected.some((s) => s.toLowerCase() === tag.toLowerCase()) &&
      tag.toLowerCase().includes(query),
  );
  // Offer to create a brand-new tag when what's typed matches nothing.
  const canCreate =
    query.length > 0 &&
    !selected.some((s) => s.toLowerCase() === query) &&
    !suggestions.some((tag) => tag.toLowerCase() === query);
  // Include any half-typed token so it is saved even without pressing Enter.
  const pendingTokens = tokenize(input).filter(
    (p) => !selected.some((s) => s.toLowerCase() === p.toLowerCase()),
  );
  const submitValue = [...selected, ...pendingTokens].join(",");

  return (
    <div className="flex flex-col gap-1.5">
      <input type="hidden" name={name} value={submitValue} />
      <label htmlFor={inputId} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <div className="relative">
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-[var(--card-border)] px-2 py-1.5">
          {selected.map((tag) => (
            <Chip key={tag} variant="soft" size="sm">
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                aria-label={`${t.removeLabel} ${tag}`}
                className="ml-1 inline-flex items-center text-muted hover:text-foreground"
              >
                <MdClose aria-hidden className="h-3 w-3" />
              </button>
            </Chip>
          ))}
          <input
            id={inputId}
            value={input}
            onChange={(event) => {
              setInput(event.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === ",") {
                event.preventDefault();
                addTokens(input);
              } else if (event.key === "Escape") {
                setOpen(false);
              } else if (
                event.key === "Backspace" &&
                input === "" &&
                selected.length > 0
              ) {
                removeTag(selected[selected.length - 1]);
              }
            }}
            placeholder={t.placeholder}
            className="min-w-28 flex-1 bg-transparent text-sm outline-none"
          />
        </div>

        {open && (matches.length > 0 || canCreate) && (
          <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-[var(--card-border)] bg-[var(--card)] py-1 shadow-lg">
            {matches.map((tag) => (
              <li key={tag}>
                {/* onMouseDown keeps the input from blurring before the click. */}
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => addTokens(tag)}
                  className="block w-full px-3 py-1.5 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10"
                >
                  {tag}
                </button>
              </li>
            ))}
            {canCreate && (
              <li>
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => addTokens(input)}
                  className="block w-full px-3 py-1.5 text-left text-sm font-medium text-[var(--accent-strong)] hover:bg-black/5 dark:hover:bg-white/10"
                >
                  {t.createLabel} “{input.trim()}”
                </button>
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
