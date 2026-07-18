"use client";

import { Button, Input, Label, TextArea, TextField } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { FiCamera } from "react-icons/fi";

import { UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";
import type { CurrentUser } from "@/lib/auth.api";
import {
  updateProfileAction,
  uploadAvatarAction,
} from "@/actions/profile.action";

const BIO_MAX = 280;

type ProfileFormProps = { user: CurrentUser };

/**
 * The "Public profile" editor: change your name, bio, and avatar picture. The
 * username and email are shown read-only (username is a one-time pick; email
 * changes are not offered in v1). Saving refreshes the app so the header
 * avatar updates immediately.
 */
export function ProfileForm({ user }: ProfileFormProps) {
  const { dict } = useI18n();
  const t = dict.settingsProfile;
  const router = useRouter();

  const [fullName, setFullName] = useState(user.full_name ?? "");
  const [bio, setBio] = useState(user.bio ?? "");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(user.avatar_url);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [isSaving, startSaving] = useTransition();

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Release the local object URL when it is replaced or on unmount.
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  async function onPickFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Reset the input so re-picking the same file fires onChange again.
    event.target.value = "";
    if (!file) {
      return;
    }
    setError(null);
    setSaved(false);
    setPreviewUrl(URL.createObjectURL(file));
    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);
    const result = await uploadAvatarAction(formData);
    setUploading(false);
    if ("url" in result) {
      setAvatarUrl(result.url);
    } else {
      setPreviewUrl(null);
      setError(t.errorUpload);
    }
  }

  function removePhoto() {
    setPreviewUrl(null);
    setAvatarUrl(null);
    setSaved(false);
  }

  function save() {
    setError(null);
    setSaved(false);
    startSaving(async () => {
      const result = await updateProfileAction({
        full_name: fullName.trim() || null,
        bio: bio.trim() || null,
        avatar_url: avatarUrl,
      });
      if (result.ok) {
        setSaved(true);
        // Re-render server components (the header avatar reads /auth/me).
        router.refresh();
      } else {
        setError(t.errorGeneric);
      }
    });
  }

  const shownAvatar = previewUrl ?? avatarUrl;

  return (
    <div className="grid gap-8 md:grid-cols-[1fr_220px] md:items-start">
      {/* Editable fields */}
      <div className="flex flex-col gap-5">
        <TextField value={fullName} onChange={setFullName} maxLength={255}>
          <Label>{t.nameLabel}</Label>
          <Input />
          <p className="mt-1 text-xs text-muted">{t.nameHint}</p>
        </TextField>

        <div className="flex flex-col gap-1.5">
          <Label>{t.bioLabel}</Label>
          <TextArea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={BIO_MAX}
            rows={3}
            fullWidth
            placeholder={t.bioPlaceholder}
            style={{ resize: "vertical" }}
          />
          <div className="flex items-center justify-between text-xs text-muted">
            <span>{t.bioHint}</span>
            <span>
              {bio.length} / {BIO_MAX}
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="settings-username">{t.usernameLabel}</Label>
          <Input id="settings-username" value={user.username} readOnly />
          <p className="text-xs text-muted">
            {t.usernameHint} printforhelp.org/{user.username}
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>{t.emailLabel}</Label>
          <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-default-100 px-3 py-2">
            <span className="truncate text-sm text-foreground/80">
              {user.email ?? t.noEmail}
            </span>
            <span className="shrink-0 rounded-full bg-default-200 px-2 py-0.5 text-xs font-medium text-muted">
              {t.emailReadOnly}
            </span>
          </div>
          <p className="text-xs text-muted">{t.emailHint}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button onPress={save} isPending={isSaving} isDisabled={uploading}>
            {isSaving ? t.saving : t.submit}
          </Button>
          {saved ? (
            <span className="text-sm text-success">{t.saved}</span>
          ) : null}
          {error ? <span className="text-sm text-danger">{error}</span> : null}
        </div>
      </div>

      {/* Profile picture */}
      <div className="flex flex-col gap-3">
        <Label>{t.pictureLabel}</Label>
        <div className="relative w-fit">
          <UserAvatar
            username={user.username}
            fullName={fullName || user.full_name}
            avatarUrl={shownAvatar}
            className="size-48"
            fallbackClassName="text-5xl"
          />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={onPickFile}
          />
          <Button
            size="sm"
            variant="secondary"
            className="absolute bottom-2 left-1/2 -translate-x-1/2 shadow-md"
            onPress={() => fileInputRef.current?.click()}
            isPending={uploading}
          >
            <FiCamera aria-hidden />
            {uploading ? t.uploading : t.pictureEdit}
          </Button>
        </div>
        {shownAvatar ? (
          <button
            type="button"
            onClick={removePhoto}
            className="self-start text-xs text-muted hover:text-danger"
          >
            {t.pictureRemove}
          </button>
        ) : null}
        <p className="text-xs leading-relaxed text-muted">{t.pictureHint}</p>
      </div>
    </div>
  );
}
