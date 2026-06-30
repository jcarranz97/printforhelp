"use client";

import { TextArea } from "@heroui/react";

import { useI18n } from "@/i18n/provider";
import type { NoticeTranslationInput } from "@/lib/notices.api";

export type TranslationDraft = {
  language: string;
  title: string;
  message: string;
  action_label: string;
  action_url: string;
};

export function emptyTranslation(language = ""): TranslationDraft {
  return { language, title: "", message: "", action_label: "", action_url: "" };
}

/** Convert editor drafts into API payloads (blanks collapse to null). */
export function toTranslationInputs(
  drafts: TranslationDraft[],
): NoticeTranslationInput[] {
  return drafts.map((draft) => {
    const url = draft.action_url.trim();
    const label = draft.action_label.trim();
    const hasAction = url !== "" && label !== "";
    return {
      language: draft.language.trim().toLowerCase(),
      title: draft.title.trim() || null,
      message: draft.message.trim(),
      action_label: hasAction ? label : null,
      action_url: hasAction ? url : null,
    };
  });
}

const FIELD_CLASS =
  "rounded-lg border border-default-200 bg-default-50 px-3 py-2 text-sm";

/** Repeatable per-language editor for a notice's title/message/CTA. */
export function NoticeTranslationsEditor({
  value,
  onChange,
}: {
  value: TranslationDraft[];
  onChange: (next: TranslationDraft[]) => void;
}) {
  const { dict } = useI18n();
  const t = dict.notices;

  function update(index: number, patch: Partial<TranslationDraft>) {
    onChange(value.map((tr, i) => (i === index ? { ...tr, ...patch } : tr)));
  }

  function remove(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  return (
    <div className="flex flex-col gap-4">
      {value.map((tr, index) => (
        <div
          // eslint-disable-next-line react/no-array-index-key
          key={index}
          className="flex flex-col gap-3 rounded-xl border border-default-200 bg-default-50/40 p-4"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t.languageLabel}</span>
              <input
                type="text"
                className={FIELD_CLASS}
                placeholder="en"
                maxLength={8}
                value={tr.language}
                onChange={(e) => update(index, { language: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t.titleLabel}</span>
              <input
                type="text"
                className={FIELD_CLASS}
                maxLength={200}
                value={tr.title}
                onChange={(e) => update(index, { title: e.target.value })}
              />
            </label>
          </div>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t.messageLabel}</span>
            <TextArea
              rows={3}
              aria-label={t.messageLabel}
              placeholder={t.messagePlaceholder}
              value={tr.message}
              onChange={(e) => update(index, { message: e.target.value })}
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t.actionLabelLabel}</span>
              <input
                type="text"
                className={FIELD_CLASS}
                maxLength={120}
                value={tr.action_label}
                onChange={(e) =>
                  update(index, { action_label: e.target.value })
                }
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t.actionUrlLabel}</span>
              <input
                type="url"
                className={FIELD_CLASS}
                placeholder={t.actionUrlPlaceholder}
                value={tr.action_url}
                onChange={(e) => update(index, { action_url: e.target.value })}
              />
            </label>
          </div>

          {value.length > 1 && (
            <button
              type="button"
              onClick={() => remove(index)}
              className="self-start text-xs text-danger hover:underline"
            >
              {t.removeLanguage}
            </button>
          )}
        </div>
      ))}

      <button
        type="button"
        onClick={() => onChange([...value, emptyTranslation()])}
        className="self-start text-sm font-medium text-primary hover:underline"
      >
        + {t.addLanguage}
      </button>
    </div>
  );
}
