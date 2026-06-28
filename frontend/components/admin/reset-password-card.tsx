"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import { type ActionState, resetPasswordAction } from "@/actions/users.action";
import { useI18n } from "@/i18n/provider";
import type { CurrentUser } from "@/lib/auth.api";

const initialState: ActionState = { error: null, success: false };

export function ResetPasswordCard({
  user,
  onClose,
}: {
  user: CurrentUser;
  onClose: () => void;
}) {
  const { dict } = useI18n();
  const t = dict.admin;
  const [state, formAction, pending] = useActionState(
    resetPasswordAction,
    initialState,
  );

  return (
    <Card variant="secondary">
      <Card.Header>
        <Card.Title>
          {t.resetTitle} {user.username}
        </Card.Title>
      </Card.Header>
      <Card.Content>
        <form action={formAction} className="flex flex-wrap items-end gap-3">
          <input type="hidden" name="userId" value={user.id} />
          <TextField
            name="new_password"
            type="text"
            isRequired
            className="min-w-64 flex-1"
          >
            <Label>{t.resetNewPassword}</Label>
            <Input autoComplete="off" placeholder={t.passwordPlaceholder} />
          </TextField>
          <Button type="submit" isPending={pending}>
            {t.resetSave}
          </Button>
          <Button type="button" variant="ghost" onPress={onClose}>
            {t.resetClose}
          </Button>
        </form>

        {state.error && (
          <Alert status="danger" className="mt-3">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{state.error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
        {state.success && (
          <Alert status="success" className="mt-3">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{t.resetSuccess}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </Card.Content>
    </Card>
  );
}
