"use client";

import { Alert, Button, Card } from "@heroui/react";
import { useState, useTransition } from "react";

import { createPageNoticeAction } from "@/actions/notices.action";
import { NoticeSeveritySelect } from "@/components/notices/notice-severity-select";
import {
  NoticeTranslationsEditor,
  type TranslationDraft,
  emptyTranslation,
  toTranslationInputs,
} from "@/components/notices/notice-translations-editor";
import { useI18n } from "@/i18n/provider";
import type { NoticeSeverity, PageScope } from "@/lib/notices.api";

const SCOPES: PageScope[] = [
  "all",
  "home",
  "centers",
  "requests",
  "parts",
  "my_contributions",
  "about",
];

/** Maintainer/admin form to publish a page banner across chosen pages. */
export function CreatePageNoticeForm() {
  const { dict } = useI18n();
  const t = dict.notices;
  const scopeLabel: Record<PageScope, string> = {
    all: t.scopeAll,
    home: t.scopeHome,
    centers: t.scopeCenters,
    requests: t.scopeRequests,
    parts: t.scopeParts,
    my_contributions: t.scopeMyContributions,
    about: t.scopeAbout,
  };

  const [severity, setSeverity] = useState<NoticeSeverity>("info");
  const [scopes, setScopes] = useState<PageScope[]>([]);
  const [drafts, setDrafts] = useState<TranslationDraft[]>([
    emptyTranslation("en"),
  ]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isPending, startTransition] = useTransition();

  function toggleScope(scope: PageScope) {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    );
  }

  function submit() {
    const translations = toTranslationInputs(drafts);
    if (scopes.length === 0) {
      setError(t.errorScopesRequired);
      return;
    }
    if (translations.some((tr) => !tr.message || !tr.language)) {
      setError(t.errorMessageRequired);
      return;
    }
    setError(null);
    setSuccess(false);
    startTransition(async () => {
      const res = await createPageNoticeAction({
        severity,
        scopes,
        translations,
      });
      if (res.error) {
        setError(res.error);
        return;
      }
      setSuccess(true);
      setSeverity("info");
      setScopes([]);
      setDrafts([emptyTranslation("en")]);
    });
  }

  return (
    <Card>
      <Card.Header>
        <Card.Title>{t.createTitle}</Card.Title>
        <Card.Description>{t.createDescription}</Card.Description>
      </Card.Header>
      <Card.Content>
        <div className="flex flex-col gap-4">
          <NoticeSeveritySelect value={severity} onChange={setSeverity} />

          <div className="flex flex-col gap-2 text-sm">
            <span className="font-medium">{t.scopesLabel}</span>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {SCOPES.map((scope) => (
                <label key={scope} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={scopes.includes(scope)}
                    onChange={() => toggleScope(scope)}
                  />
                  {scopeLabel[scope]}
                </label>
              ))}
            </div>
          </div>

          <NoticeTranslationsEditor value={drafts} onChange={setDrafts} />

          {error && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{error}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}
          {success && (
            <Alert status="success">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{t.createSuccess}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}

          <Button isPending={isPending} onPress={submit} className="self-start">
            {t.createTitle}
          </Button>
        </div>
      </Card.Content>
    </Card>
  );
}
