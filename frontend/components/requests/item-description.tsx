"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { setItemDescriptionAction } from "@/actions/requests.action";
import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { useI18n } from "@/i18n/provider";

/**
 * Optional Markdown notes about a specific request item (e.g. why the part is
 * needed). Shown to everyone on the shareable item page; the requester can
 * add or edit it inline. Renders nothing when it is empty and the viewer
 * cannot manage the item.
 */
export function ItemDescription({
  requestId,
  itemId,
  description,
  canManage,
}: {
  requestId: string;
  itemId: string;
  description: string | null;
  canManage: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.itemDescription;
  const router = useRouter();
  const [current, setCurrent] = useState(description ?? "");
  const [draft, setDraft] = useState(current);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function save() {
    setError(null);
    startTransition(async () => {
      const res = await setItemDescriptionAction(requestId, itemId, draft);
      if (res.error) {
        setError(res.error);
        return;
      }
      setCurrent(draft.trim());
      setEditing(false);
      router.refresh();
    });
  }

  if (!current && !canManage) {
    return null;
  }

  return (
    <section className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-muted">{t.heading}</h2>
        {canManage && !editing && (
          <button
            type="button"
            onClick={() => {
              setDraft(current);
              setEditing(true);
            }}
            className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
          >
            {current ? t.edit : t.add}
          </button>
        )}
      </div>

      {editing ? (
        <div className="flex flex-col gap-2">
          <MarkdownEditor
            value={draft}
            onChange={setDraft}
            rows={5}
            placeholder={t.placeholder}
          />
          {error && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{error}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}
          <div className="flex items-center gap-3">
            <Button type="button" size="sm" onPress={save} isPending={pending}>
              {t.save}
            </Button>
            <button
              type="button"
              onClick={() => {
                setDraft(current);
                setEditing(false);
                setError(null);
              }}
              className="text-xs text-muted hover:underline"
            >
              {t.cancel}
            </button>
          </div>
        </div>
      ) : current ? (
        <div className="max-w-2xl">
          <CollapsibleMarkdown source={current} />
        </div>
      ) : (
        <p className="text-sm text-muted">{t.emptyOwner}</p>
      )}
    </section>
  );
}
