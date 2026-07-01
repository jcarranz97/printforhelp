"use client";

import { Alert, Button, Chip } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState } from "react";

import { TagInput } from "@/components/forms/tag-input";
import {
  type TrackingState,
  editRecordTagsAction,
} from "@/actions/tracking.action";
import { useI18n } from "@/i18n/provider";

const initialState: TrackingState = { error: null };

/** Inline tag editor for one tracking record (author / owner / admin only). */
export function RecordTagsEditor({
  recordId,
  tags,
  allTags,
  revalidate,
}: {
  recordId: string;
  tags: string[];
  allTags: string[];
  revalidate: string;
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const router = useRouter();
  const action = editRecordTagsAction.bind(null, recordId, revalidate);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [editing, setEditing] = useState(false);

  // Collapse back to chips and re-fetch so the saved tags render immediately
  // (the collapsed view reads the server-provided tags, not local state).
  useEffect(() => {
    if (state.success) {
      setEditing(false);
      router.refresh();
    }
  }, [state, router]);

  if (!editing) {
    return (
      <div className="flex flex-wrap items-center gap-1.5">
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
