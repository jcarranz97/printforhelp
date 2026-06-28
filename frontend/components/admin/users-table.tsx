"use client";

import {
  Alert,
  Button,
  Chip,
  type Key,
  ListBox,
  Select,
  Table,
} from "@heroui/react";
import { useState, useTransition } from "react";

import { setActiveAction, updateRoleAction } from "@/actions/users.action";
import { useI18n } from "@/i18n/provider";
import type { CurrentUser, UserRole } from "@/lib/auth.api";

import { ResetPasswordCard } from "./reset-password-card";

export function UsersTable({
  users,
  currentUserId,
}: {
  users: CurrentUser[];
  currentUserId: string;
}) {
  const { dict } = useI18n();
  const t = dict.admin;
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [resetUser, setResetUser] = useState<CurrentUser | null>(null);

  function changeRole(userId: string, value: Key | null) {
    if (value === null) {
      return;
    }
    setError(null);
    startTransition(async () => {
      const res = await updateRoleAction(userId, String(value) as UserRole);
      if (res.error) {
        setError(res.error);
      }
    });
  }

  function toggleActive(user: CurrentUser) {
    setError(null);
    startTransition(async () => {
      const res = await setActiveAction(user.id, !user.active);
      if (res.error) {
        setError(res.error);
      }
    });
  }

  return (
    <div className="flex flex-col gap-4">
      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      <Table>
        <Table.ScrollContainer>
          <Table.Content
            aria-label={t.tableAriaLabel}
            className="min-w-[640px]"
          >
            <Table.Header>
              <Table.Column isRowHeader>{t.colUser}</Table.Column>
              <Table.Column>{t.colRole}</Table.Column>
              <Table.Column>{t.colStatus}</Table.Column>
              <Table.Column className="text-end">{t.colActions}</Table.Column>
            </Table.Header>
            <Table.Body>
              {users.map((user) => {
                const isSelf = user.id === currentUserId;
                return (
                  <Table.Row key={user.id} id={user.id}>
                    <Table.Cell className="font-medium">
                      {user.username}
                      {isSelf && (
                        <span className="ml-2 text-xs text-muted">{t.you}</span>
                      )}
                    </Table.Cell>
                    <Table.Cell className="min-w-44">
                      <Select
                        aria-label={`${t.roleAriaLabel} ${user.username}`}
                        value={user.role}
                        isDisabled={isSelf || isPending}
                        onChange={(value) => changeRole(user.id, value)}
                      >
                        <Select.Trigger>
                          <Select.Value />
                          <Select.Indicator />
                        </Select.Trigger>
                        <Select.Popover>
                          <ListBox>
                            <ListBox.Item id="user" textValue={t.roleUser}>
                              {t.roleUser}
                              <ListBox.ItemIndicator />
                            </ListBox.Item>
                            <ListBox.Item
                              id="maintainer"
                              textValue={t.roleMaintainer}
                            >
                              {t.roleMaintainer}
                              <ListBox.ItemIndicator />
                            </ListBox.Item>
                            <ListBox.Item id="admin" textValue={t.roleAdmin}>
                              {t.roleAdmin}
                              <ListBox.ItemIndicator />
                            </ListBox.Item>
                          </ListBox>
                        </Select.Popover>
                      </Select>
                    </Table.Cell>
                    <Table.Cell>
                      <Chip
                        color={user.active ? "success" : "danger"}
                        size="sm"
                        variant="soft"
                      >
                        {user.active ? t.statusActive : t.statusInactive}
                      </Chip>
                    </Table.Cell>
                    <Table.Cell>
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onPress={() => setResetUser(user)}
                        >
                          {t.passwordButton}
                        </Button>
                        <Button
                          size="sm"
                          variant={user.active ? "danger-soft" : "secondary"}
                          isDisabled={isSelf || isPending}
                          onPress={() => toggleActive(user)}
                        >
                          {user.active ? t.deactivate : t.activate}
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

      {resetUser && (
        <ResetPasswordCard
          key={resetUser.id}
          user={resetUser}
          onClose={() => setResetUser(null)}
        />
      )}
    </div>
  );
}
