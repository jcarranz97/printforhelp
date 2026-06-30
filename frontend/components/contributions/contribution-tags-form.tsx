"use client";

import { Alert, Button, Chip, Tooltip } from "@heroui/react";
import { useActionState, useEffect, useState } from "react";
import { MdInfoOutline } from "react-icons/md";

import { TagInput } from "@/components/forms/tag-input";
import {
  type SetTagsState,
  setContributionTagsAction,
} from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";

const initialState: SetTagsState = { error: null };

/** Inline tag editor for a contribution: collapses to chips plus an add/edit
 * affordance, and expands into the shared creatable {@link TagInput}. */
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

  // Collapse back to the chip view once a save succeeds.
  useEffect(() => {
    if (state.success) {
      setEditing(false);
    }
  }, [state]);

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
          onClick={() => setEditing(true)}
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

  return (
    <form action={formAction} className="flex w-full flex-col gap-2">
      <TagInput
        name="tags"
        label={t.tagsLabel}
        defaultTags={tags}
        suggestions={allTags}
      />
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
