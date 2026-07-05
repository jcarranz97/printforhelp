"use client";

import { Alert, Button, Input, Label, Modal, TextField } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { chooseUsernameAction } from "@/actions/auth.action";
import { useI18n } from "@/i18n/provider";

/**
 * Mandatory modal shown by the root layout when a Google sign-up still
 * carries an auto-generated username. It cannot be dismissed — the user
 * must pick a username, which refreshes the page and removes the modal.
 */
export function ChooseUsernameModal({ suggestion }: { suggestion: string }) {
  const { dict } = useI18n();
  const t = dict.chooseUsername;
  const router = useRouter();
  const [value, setValue] = useState(suggestion);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function submit() {
    startTransition(async () => {
      const result = await chooseUsernameAction(value);
      if (result.error) {
        setError(result.error);
        return;
      }
      router.refresh();
    });
  }

  return (
    // isOpen is always true and there is no close handler, so the modal
    // stays up until a username is successfully chosen.
    <Modal.Backdrop isOpen>
      <Modal.Container>
        <Modal.Dialog className="sm:max-w-[380px]">
          <Modal.Header>
            <Modal.Heading>{t.title}</Modal.Heading>
          </Modal.Header>
          <Modal.Body className="flex flex-col gap-4">
            <p className="text-sm text-muted">{t.description}</p>
            <TextField
              value={value}
              onChange={(next) => {
                setValue(next);
                // Clear a stale "taken"/"invalid" message as soon as the
                // user starts changing the name.
                if (error) setError(null);
              }}
              isInvalid={Boolean(error)}
              isDisabled={isPending}
            >
              <Label>{t.label}</Label>
              <Input autoComplete="username" placeholder={t.placeholder} />
            </TextField>
            <p className="text-xs text-muted">{t.hint}</p>
            {error && (
              <Alert status="danger">
                <Alert.Indicator />
                <Alert.Content>
                  <Alert.Description>{error}</Alert.Description>
                </Alert.Content>
              </Alert>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button isPending={isPending} onPress={submit} className="w-full">
              {isPending ? t.submitting : t.submit}
            </Button>
          </Modal.Footer>
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  );
}
