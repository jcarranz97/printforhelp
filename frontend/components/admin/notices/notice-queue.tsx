"use client";

import { Alert, Button, Chip, Table } from "@heroui/react";
import { useState, useTransition } from "react";

import {
  approveNoticeAction,
  declineNoticeAction,
} from "@/actions/notices.action";
import { useI18n } from "@/i18n/provider";
import { type Notice, resolveTranslation } from "@/lib/notices.api";

import {
  severityChipColor,
  severityLabel,
  targetLabel,
} from "./notice-display";

/** Moderation queue of pending entity-notice requests (approve / decline). */
export function NoticeQueue({ notices }: { notices: Notice[] }) {
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
        <h2 className="text-lg font-semibold">{t.queueTitle}</h2>
        <p className="text-sm text-muted">{t.queueDescription}</p>
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
        <p className="text-sm text-muted">{t.queueEmpty}</p>
      ) : (
        <Table>
          <Table.ScrollContainer>
            <Table.Content aria-label={t.queueTitle} className="min-w-[640px]">
              <Table.Header>
                <Table.Column isRowHeader>{t.colMessage}</Table.Column>
                <Table.Column>{t.colTarget}</Table.Column>
                <Table.Column>{t.colSeverity}</Table.Column>
                <Table.Column className="text-end">{t.colActions}</Table.Column>
              </Table.Header>
              <Table.Body>
                {notices.map((notice) => {
                  const tr = resolveTranslation(notice, locale);
                  return (
                    <Table.Row key={notice.id} id={notice.id}>
                      <Table.Cell className="max-w-sm">
                        <span className="line-clamp-2">{tr?.message}</span>
                      </Table.Cell>
                      <Table.Cell>{targetLabel(notice, t)}</Table.Cell>
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
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            isDisabled={isPending}
                            onPress={() =>
                              run(() => approveNoticeAction(notice.id))
                            }
                          >
                            {t.approve}
                          </Button>
                          <Button
                            size="sm"
                            variant="danger-soft"
                            isDisabled={isPending}
                            onPress={() =>
                              run(() => declineNoticeAction(notice.id))
                            }
                          >
                            {t.decline}
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
