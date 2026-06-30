"use client";

import { Alert, Button, Chip, Table } from "@heroui/react";
import { useState, useTransition } from "react";

import {
  deleteNoticeAction,
  toggleNoticeAction,
} from "@/actions/notices.action";
import { useI18n } from "@/i18n/provider";
import { type Notice, resolveTranslation } from "@/lib/notices.api";

import {
  severityChipColor,
  severityLabel,
  statusChipColor,
  statusLabel,
  targetLabel,
} from "./notice-display";

/** Table of approved notices with enable/disable and delete controls. */
export function NoticesTable({ notices }: { notices: Notice[] }) {
  const { dict, locale } = useI18n();
  const t = dict.notices;
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function run(action: () => Promise<{ error: string | null }>) {
    setError(null);
    startTransition(async () => {
      const res = await action();
      if (res.error) {
        setError(res.error);
      }
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold">{t.listTitle}</h2>
      </div>

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      {notices.length === 0 ? (
        <p className="text-sm text-muted">{t.listEmpty}</p>
      ) : (
        <Table>
          <Table.ScrollContainer>
            <Table.Content aria-label={t.listTitle} className="min-w-[760px]">
              <Table.Header>
                <Table.Column isRowHeader>{t.colMessage}</Table.Column>
                <Table.Column>{t.colTarget}</Table.Column>
                <Table.Column>{t.colSeverity}</Table.Column>
                <Table.Column>{t.colStatus}</Table.Column>
                <Table.Column>{t.colLanguages}</Table.Column>
                <Table.Column className="text-end">{t.colActions}</Table.Column>
              </Table.Header>
              <Table.Body>
                {notices.map((notice) => {
                  const tr = resolveTranslation(notice, locale);
                  const languages = notice.translations
                    .map((x) => x.language)
                    .join(", ");
                  return (
                    <Table.Row key={notice.id} id={notice.id}>
                      <Table.Cell className="max-w-xs">
                        <span className="line-clamp-2">{tr?.message}</span>
                      </Table.Cell>
                      <Table.Cell>
                        {targetLabel(notice, t)}
                        {notice.target_type === null &&
                          notice.scopes.length > 0 && (
                            <span className="block text-xs text-muted">
                              {notice.scopes.join(", ")}
                            </span>
                          )}
                      </Table.Cell>
                      <Table.Cell>
                        <Chip
                          color={severityChipColor(notice.severity)}
                          size="sm"
                          variant="soft"
                        >
                          {severityLabel(notice.severity, t)}
                        </Chip>
                      </Table.Cell>
                      <Table.Cell>
                        <div className="flex flex-col gap-1">
                          <Chip
                            color={statusChipColor(notice.status)}
                            size="sm"
                            variant="soft"
                          >
                            {statusLabel(notice.status, t)}
                          </Chip>
                          <span className="text-xs text-muted">
                            {notice.enabled ? t.enabledOn : t.enabledOff}
                          </span>
                        </div>
                      </Table.Cell>
                      <Table.Cell className="uppercase">{languages}</Table.Cell>
                      <Table.Cell>
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            isDisabled={isPending}
                            onPress={() =>
                              run(() => toggleNoticeAction(notice.id))
                            }
                          >
                            {notice.enabled ? t.disable : t.enable}
                          </Button>
                          <Button
                            size="sm"
                            variant="danger-soft"
                            isDisabled={isPending}
                            onPress={() =>
                              run(() => deleteNoticeAction(notice.id))
                            }
                          >
                            {t.delete}
                          </Button>
                        </div>
                      </Table.Cell>
                    </Table.Row>
                  );
                })}
              </Table.Body>
            </Table.Content>
          </Table.ScrollContainer>
        </Table>
      )}
    </div>
  );
}
