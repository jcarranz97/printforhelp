"use client";

import {
  AlertDialog,
  Button,
  Description,
  Input,
  Label,
  TextField,
  toast,
} from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { changeUsernameAction } from "@/actions/username.action";
import { useI18n } from "@/i18n/provider";
import type { CurrentUser } from "@/lib/auth.api";

/** Map a backend error code to localised copy. */
function messageFor(
  code: string,
  t: ReturnType<typeof useI18n>["dict"]["settingsProfile"],
): string {
  switch (code) {
    case "USERNAME_TAKEN":
      return t.usernameTaken;
    case "USERNAME_RESERVED":
      return t.usernameReserved;
    case "USERNAME_CHANGE_TOO_SOON":
      return t.usernameTooSoon;
    case "INVALID_USERNAME":
      return t.usernameFormat;
    default:
      return t.errorGeneric;
  }
}

/**
 * The public handle, editable but rate-limited.
 *
 * Renaming breaks every existing link to the profile, so it is a deliberate
 * action: confirmed in a dialog, saved on its own (not folded into the
 * name/bio button), and locked while the server-side cooldown is running.
 */
export function UsernameField({ user }: { user: CurrentUser }) {
  const { dict, locale } = useI18n();
  const t = dict.settingsProfile;
  const router = useRouter();

  const [value, setValue] = useState(user.username);
  const [confirming, setConfirming] = useState(false);
  const [isSaving, startSaving] = useTransition();

  const lockedUntil = user.username_change_available_at
    ? new Date(user.username_change_available_at)
    : null;
  // The server enforces this; the UI only mirrors it so the field explains
  // itself instead of failing on submit.
  const locked = lockedUntil !== null && lockedUntil > new Date();
  const changed = value.trim() !== "" && value.trim() !== user.username;

  function save() {
    setConfirming(false);
    startSaving(async () => {
      const result = await changeUsernameAction(value);
      if (result.ok) {
        toast.success(t.usernameSaved);
        router.refresh();
      } else {
        toast.danger(messageFor(result.errorCode, t));
        setValue(user.username);
      }
    });
  }

  return (
    <div className="flex flex-col gap-1.5">
      {/* Disabled (not merely read-only) during the cooldown: the field is
          genuinely unavailable, and the disabled styling says so at a glance
          instead of looking like an editable input that silently ignores you. */}
      <TextField
        isDisabled={locked}
        value={value}
        onChange={setValue}
        maxLength={50}
        className="gap-1.5"
      >
        <Label>{t.usernameLabel}</Label>
        <div className="flex items-center gap-2">
          <Input id="settings-username" className="flex-1" />
          {changed && !locked ? (
            <Button
              size="sm"
              variant="secondary"
              onPress={() => setConfirming(true)}
              isPending={isSaving}
            >
              {t.usernameChange}
            </Button>
          ) : null}
        </div>
        {/* Why it is locked comes first: it explains the state of the field
            the reader is looking at, before the general handle/URL note. */}
        {locked && lockedUntil ? (
          <Description className="text-xs text-warning">
            {t.usernameCooldown.replace(
              "{date}",
              new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
                dateStyle: "long",
              }).format(lockedUntil),
            )}
          </Description>
        ) : null}
        <Description className="text-xs text-muted">
          {t.usernameHint} printforhelp.org/{user.username}
        </Description>
      </TextField>

      <AlertDialog.Backdrop
        isOpen={confirming}
        onOpenChange={(open) => !open && setConfirming(false)}
      >
        <AlertDialog.Container>
          <AlertDialog.Dialog>
            <AlertDialog.Header>
              <AlertDialog.Heading>
                {t.usernameConfirmTitle}
              </AlertDialog.Heading>
            </AlertDialog.Header>
            <AlertDialog.Body>
              {/* Spell out both consequences: dead links, and the wait. */}
              <p>
                {t.usernameConfirmBody
                  .replace("{from}", user.username)
                  .replace("{to}", value.trim())}
              </p>
            </AlertDialog.Body>
            <AlertDialog.Footer>
              <Button variant="tertiary" onPress={() => setConfirming(false)}>
                {t.pictureCancel}
              </Button>
              <Button onPress={save}>{t.usernameChange}</Button>
            </AlertDialog.Footer>
          </AlertDialog.Dialog>
        </AlertDialog.Container>
      </AlertDialog.Backdrop>
    </div>
  );
}
