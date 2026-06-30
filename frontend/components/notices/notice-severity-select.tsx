"use client";

import { type Key, ListBox, Select } from "@heroui/react";

import { useI18n } from "@/i18n/provider";
import type { NoticeSeverity } from "@/lib/notices.api";

const SEVERITIES: NoticeSeverity[] = ["info", "success", "warning", "critical"];

/** Severity dropdown shared by the create-banner and request-notice forms. */
export function NoticeSeveritySelect({
  value,
  onChange,
}: {
  value: NoticeSeverity;
  onChange: (severity: NoticeSeverity) => void;
}) {
  const { dict } = useI18n();
  const t = dict.notices;
  const label = (severity: NoticeSeverity) =>
    severity === "info"
      ? t.severityInfo
      : severity === "success"
        ? t.severitySuccess
        : severity === "warning"
          ? t.severityWarning
          : t.severityCritical;

  return (
    <div className="flex max-w-xs flex-col gap-1 text-sm">
      <span className="font-medium">{t.severityLabel}</span>
      <Select
        aria-label={t.severityLabel}
        value={value}
        onChange={(key: Key | null) =>
          onChange((key as NoticeSeverity) ?? "info")
        }
      >
        <Select.Trigger>
          <Select.Value />
          <Select.Indicator />
        </Select.Trigger>
        <Select.Popover>
          <ListBox>
            {SEVERITIES.map((severity) => (
              <ListBox.Item
                key={severity}
                id={severity}
                textValue={label(severity)}
              >
                {label(severity)}
                <ListBox.ItemIndicator />
              </ListBox.Item>
            ))}
          </ListBox>
        </Select.Popover>
      </Select>
    </div>
  );
}
