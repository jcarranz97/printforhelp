"use client";

import { Alert, Button } from "@heroui/react";
import { useState, useTransition } from "react";

import { requestNoticeAction } from "@/actions/notices.action";
import { useI18n } from "@/i18n/provider";
import type { NoticeSeverity, NoticeTargetType } from "@/lib/notices.api";

import { NoticeSeveritySelect } from "./notice-severity-select";
import {
  NoticeTranslationsEditor,
  type TranslationDraft,
  emptyTranslation,
  toTranslationInputs,
} from "./notice-translations-editor";

/**
 * Inline control on an entity detail page that lets the owner (or a
 * maintainer) request a notice for that item. Owners get a pending request;
 * maintainers publish immediately (the backend decides by role).
 */
export function RequestNotice({
  targetType,
  targetId,
  revalidate,
  isMaintainer,
}: {
  targetType: NoticeTargetType;
  targetId: string;
  revalidate: string;
  isMaintainer: boolean;
}) {
  const { dict, locale } = useI18n();
  const t = dict.notices;
  const [open, setOpen] = useState(false);
  const [severity, setSeverity] = useState<NoticeSeverity>("info");
  const [drafts, setDrafts] = useState<TranslationDraft[]>([
    emptyTranslation(locale),
  ]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function reset() {
    setSeverity("info");
    setDrafts([emptyTranslation(locale)]);
    setError(null);
  }

  function submit() {
    const translations = toTranslationInputs(drafts);
    if (translations.some((tr) => !tr.message || !tr.language)) {
      setError(t.errorMessageRequired);
      return;
    }
    setError(null);
    startTransition(async () => {
      const res = await requestNoticeAction(revalidate, {
        severity,
        target_type: targetType,
        target_id: targetId,
        translations,
      });
      if (res.error) {
        setError(res.error);
        return;
      }
      setSuccess(
        isMaintainer ? t.requestSuccessApproved : t.requestSuccessPending,
      );
      setOpen(false);
      reset();
    });
  }

  if (!open) {
    return (
      <div className="mt-6 flex flex-col gap-2">
        {success && (
          <Alert status="success">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{success}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
        <Button
          size="sm"
          variant="secondary"
          className="self-start"
          onPress={() => {
            setSuccess(null);
            setOpen(true);
          }}
        >
          {t.requestButton}
        </Button>
      </div>
    );
  }

  return (
    <div className="mt-6 flex flex-col gap-3 rounded-xl border border-default-200 bg-default-50/40 p-4">
      <div>
        <h3 className="font-semibold">{t.requestTitle}</h3>
        <p className="text-sm text-muted">
          {isMaintainer
            ? t.requestDescriptionMaintainer
            : t.requestDescriptionOwner}
        </p>
      </div>
      <NoticeSeveritySelect value={severity} onChange={setSeverity} />
      <NoticeTranslationsEditor value={drafts} onChange={setDrafts} />
      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
      <div className="flex gap-2">
        <Button size="sm" isPending={isPending} onPress={submit}>
          {t.submit}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onPress={() => {
            setOpen(false);
            reset();
          }}
        >
          {t.cancel}
        </Button>
      </div>
    </div>
  );
}
