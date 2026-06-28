"use client";

import {
  Alert,
  Button,
  Card,
  Input,
  Label,
  ListBox,
  Select,
  TextField,
} from "@heroui/react";
import { useActionState, useEffect, useRef } from "react";

import { type ActionState, createUserAction } from "@/actions/users.action";
import { useI18n } from "@/i18n/provider";

const initialState: ActionState = { error: null, success: false };

export function CreateUserForm() {
  const { dict } = useI18n();
  const t = dict.admin;
  const [state, formAction, pending] = useActionState(
    createUserAction,
    initialState,
  );
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (state.success) {
      formRef.current?.reset();
    }
  }, [state.success]);

  return (
    <Card>
      <Card.Header>
        <Card.Title>{t.createTitle}</Card.Title>
        <Card.Description>{t.createDescription}</Card.Description>
      </Card.Header>
      <Card.Content>
        <form ref={formRef} action={formAction} className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <TextField name="username" type="text" isRequired>
              <Label>{t.username}</Label>
              <Input autoComplete="off" placeholder={t.usernamePlaceholder} />
            </TextField>

            <TextField name="password" type="text" isRequired>
              <Label>{t.password}</Label>
              <Input autoComplete="off" placeholder={t.passwordPlaceholder} />
            </TextField>

            <Select
              name="role"
              defaultValue="user"
              placeholder={t.rolePlaceholder}
            >
              <Label>{t.role}</Label>
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
                  <ListBox.Item id="maintainer" textValue={t.roleMaintainer}>
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
          </div>

          {state.error && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{state.error}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}
          {state.success && (
            <Alert status="success">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{t.createSuccess}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}

          <Button type="submit" isPending={pending} className="self-start">
            {t.createSubmit}
          </Button>
        </form>
      </Card.Content>
    </Card>
  );
}
