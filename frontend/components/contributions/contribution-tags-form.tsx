"use client";

import { Alert, Button, Chip, Label, Tooltip } from "@heroui/react";
import { useActionState, useEffect, useState } from "react";
import { MdClose, MdInfoOutline } from "react-icons/md";

import {
  type SetTagsState,
  setContributionTagsAction,
} from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";

const initialState: SetTagsState = { error: null };

/** Split raw input on commas into trimmed, non-empty tag tokens. */
function tokenize(raw: string): string[] {
  return raw
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

/** Inline tag editor for a contribution: a GitHub/JIRA-style token input
 * where the maker can reuse their existing tags or type a brand-new one
 * (which is just added). Collapses to chips plus an add/edit affordance. */
export function ContributionTagsForm({
  contributionId,
  tags,
  allTags,
}: {
  contributionId: string;
  tags: string[];
  allTags: string[];
}) {
  const { dict } = useI18n();
  const t = dict.myContributions;
  const action = setContributionTagsAction.bind(null, contributionId);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [editing, setEditing] = useState(false);
  const [selected, setSelected] = useState<string[]>(tags);
  const [input, setInput] = useState("");
  const [open, setOpen] = useState(false);

  // Collapse back to the chip view once a save succeeds.
  useEffect(() => {
    if (state.success) {
      setEditing(false);
    }
  }, [state]);

  function startEditing() {
    setSelected(tags);
    setInput("");
    setEditing(true);
  }

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

  if (!editing) {
    return (
      <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">
        {tags.map((tag) => (
          <Chip key={tag} variant="soft" size="sm">
            {tag}
          </Chip>
        ))}
        <button
          type="button"
          onClick={startEditing}
          className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
        >
          {tags.length > 0 ? t.editTags : t.addTags}
        </button>
        <Tooltip delay={0}>
          <Tooltip.Trigger
            aria-label={t.tagsHelpLabel}
            className="inline-flex cursor-help items-center text-muted hover:text-foreground"
          >
            <MdInfoOutline aria-hidden className="h-4 w-4" />
          </Tooltip.Trigger>
          <Tooltip.Content showArrow>
            <Tooltip.Arrow />
            <p className="max-w-xs text-xs">{t.tagsHelp}</p>
          </Tooltip.Content>
        </Tooltip>
      </div>
    );
  }

  // Existing tags not yet selected, matching what's being typed.
  const query = input.trim().toLowerCase();
  const suggestions = allTags.filter(
    (tag) =>
      !selected.some((s) => s.toLowerCase() === tag.toLowerCase()) &&
      tag.toLowerCase().includes(query),
  );
  // Offer to create a brand-new tag when what's typed matches nothing.
  const canCreate =
    query.length > 0 &&
    !selected.some((s) => s.toLowerCase() === query) &&
    !allTags.some((tag) => tag.toLowerCase() === query);
  // Include any half-typed token so it is saved even without pressing Enter.
  const pendingTokens = tokenize(input).filter(
    (p) => !selected.some((s) => s.toLowerCase() === p.toLowerCase()),
  );
  const submitValue = [...selected, ...pendingTokens].join(",");

  return (
    <form action={formAction} className="flex w-full flex-col gap-2">
      <input type="hidden" name="tags" value={submitValue} />
      <Label className="text-xs">{t.tagsLabel}</Label>
      <div className="relative">
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-[var(--card-border)] px-2 py-1.5">
          {selected.map((tag) => (
            <Chip key={tag} variant="soft" size="sm">
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                aria-label={`${t.removeTag} ${tag}`}
                className="ml-1 inline-flex items-center text-muted hover:text-foreground"
              >
                <MdClose aria-hidden className="h-3 w-3" />
              </button>
            </Chip>
          ))}
          <input
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
            placeholder={t.tagsPlaceholder}
            className="min-w-28 flex-1 bg-transparent text-sm outline-none"
          />
        </div>

        {open && (suggestions.length > 0 || canCreate) && (
          <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-[var(--card-border)] bg-[var(--card)] py-1 shadow-lg">
            {suggestions.map((tag) => (
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
                  {t.createTag} “{input.trim()}”
                </button>
              </li>
            )}
          </ul>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button type="submit" size="sm" variant="secondary" isPending={pending}>
          {t.saveTags}
        </Button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          className="text-xs text-muted hover:underline"
        >
          {t.cancel}
        </button>
      </div>

      {state.error && (
        <Alert status="danger" className="w-full">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{state.error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
    </form>
  );
}
