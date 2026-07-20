"use client";

import {
  Button,
  Input,
  Label,
  TextArea,
  TextField,
  toast,
} from "@heroui/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { type AvatarCrop, FULL_CROP } from "@/components/common/user-avatar";
import { AvatarEditorModal } from "@/components/settings/avatar-editor-modal";
import { AvatarField } from "@/components/settings/avatar-field";
import { useI18n } from "@/i18n/provider";
import type { CurrentUser } from "@/lib/auth.api";
import {
  updateAvatarAction,
  updateProfileAction,
  uploadAvatarAction,
} from "@/actions/profile.action";

const BIO_MAX = 280;

type ProfileFormProps = { user: CurrentUser };

/**
 * The "Public profile" editor — everything a visitor sees on `/<username>`:
 *
 * * **Name and bio** — the fields behind the form's button.
 * * **Profile picture** — saved the moment a crop is applied, not with the
 *   button, since choosing a photo already ends in an explicit "Apply".
 *
 * The handle and email live on the Account tab instead: they identify the
 * account rather than describe the person, and each saves itself.
 *
 * Each save refreshes the app so the header avatar and greeting stay in step.
 */
export function ProfileForm({ user }: ProfileFormProps) {
  const { dict } = useI18n();
  const t = dict.settingsProfile;
  const router = useRouter();

  const [fullName, setFullName] = useState(user.full_name ?? "");
  const [bio, setBio] = useState(user.bio ?? "");
  // The *saved* picture. The photo is persisted the moment it is applied, so
  // this always mirrors what is on the server — never a pending edit.
  const [avatarUrl, setAvatarUrl] = useState<string | null>(user.avatar_url);
  const [crop, setCrop] = useState<AvatarCrop>({
    x: user.avatar_crop_x,
    y: user.avatar_crop_y,
    w: user.avatar_crop_w,
    h: user.avatar_crop_h,
  });
  // A freshly uploaded picture awaiting a crop. Kept apart from `avatarUrl` so
  // cancelling the editor discards it and leaves the saved photo alone.
  const [draftUrl, setDraftUrl] = useState<string | null>(null);
  const [draftPreview, setDraftPreview] = useState<string | null>(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [savingAvatar, setSavingAvatar] = useState(false);
  const [isSaving, startSaving] = useTransition();

  // Release the local object URL when it is replaced or on unmount.
  useEffect(() => {
    return () => {
      if (draftPreview) {
        URL.revokeObjectURL(draftPreview);
      }
    };
  }, [draftPreview]);

  async function uploadFile(file: File) {
    setDraftPreview(URL.createObjectURL(file));
    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);
    const result = await uploadAvatarAction(formData);
    setUploading(false);
    if ("url" in result) {
      setDraftUrl(result.url);
      // Go straight into the crop editor: choosing what the avatar shows is
      // part of adding the photo, not a separate chore.
      setEditorOpen(true);
    } else {
      setDraftPreview(null);
      toast.danger(t.errorUpload);
    }
  }

  /** Persist the picture immediately — it is not part of the name/bio form. */
  async function persistAvatar(url: string | null, next: AvatarCrop) {
    setSavingAvatar(true);
    const result = await updateAvatarAction({
      avatar_url: url,
      avatar_crop_x: next.x,
      avatar_crop_y: next.y,
      avatar_crop_w: next.w,
      avatar_crop_h: next.h,
    });
    setSavingAvatar(false);
    if (result.ok) {
      setAvatarUrl(url);
      setCrop(next);
      toast.success(url ? t.pictureSaved : t.pictureRemoved);
      // Re-render server components (the header avatar reads /auth/me).
      router.refresh();
    } else {
      toast.danger(t.errorGeneric);
    }
    return result.ok;
  }

  async function applyCrop(next: AvatarCrop) {
    const url = draftUrl ?? avatarUrl;
    setEditorOpen(false);
    if (await persistAvatar(url, next)) {
      setDraftUrl(null);
      setDraftPreview(null);
    }
  }

  function cancelEditor() {
    // Discard a picture that was uploaded but never applied.
    setDraftUrl(null);
    setDraftPreview(null);
    setEditorOpen(false);
  }

  function removePhoto() {
    void persistAvatar(null, FULL_CROP);
  }

  function save() {
    startSaving(async () => {
      const result = await updateProfileAction({
        full_name: fullName.trim() || null,
        bio: bio.trim() || null,
      });
      if (result.ok) {
        toast.success(t.saved);
        router.refresh();
      } else {
        toast.danger(t.errorGeneric);
      }
    });
  }

  // The field shows the saved photo; the editor shows the draft when there is
  // one (its local preview renders instantly, before the upload round-trips).
  const editorImage = draftPreview ?? draftUrl ?? avatarUrl;
  // Compared against what is saved, so the button only offers a real change.
  const aboutChanged =
    fullName.trim() !== (user.full_name ?? "") ||
    bio.trim() !== (user.bio ?? "");

  return (
    <div className="grid gap-8 md:grid-cols-[1fr_220px] md:items-start">
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

        <div className="flex flex-wrap items-center gap-3">
          {/* Disabled rather than hidden while unchanged: with two fields
              above it, a button appearing and vanishing would shift the
              layout as you type. */}
          <Button
            onPress={save}
            isPending={isSaving}
            isDisabled={uploading || !aboutChanged}
          >
            {isSaving ? t.saving : t.submit}
          </Button>
        </div>
      </div>

      {/* Profile picture — saved on Apply, not with the form's button */}
      <AvatarField
        username={user.username}
        fullName={fullName || user.full_name}
        avatarUrl={avatarUrl}
        crop={crop}
        uploading={uploading}
        savingAvatar={savingAvatar}
        onPickFile={uploadFile}
        onAdjust={() => setEditorOpen(true)}
        onRemove={removePhoto}
      />

      {editorImage ? (
        <AvatarEditorModal
          isOpen={editorOpen}
          username={user.username}
          fullName={fullName || user.full_name}
          imageUrl={editorImage}
          // A brand-new picture starts uncropped (the editor centres it once
          // it knows the dimensions); an existing one reopens as saved.
          initialCrop={draftUrl ? FULL_CROP : crop}
          onApply={(next) => void applyCrop(next)}
          onCancel={cancelEditor}
        />
      ) : null}
    </div>
  );
}
