"use client";

import { Button, Label } from "@heroui/react";
import { useRef } from "react";
import { FiCamera, FiCrop } from "react-icons/fi";

import { type AvatarCrop, UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";

type AvatarFieldProps = {
  username: string;
  fullName: string | null;
  /** The picture to show: a freshly picked local preview or the stored URL. */
  avatarUrl: string | null;
  crop: AvatarCrop;
  uploading: boolean;
  /** True while the applied picture is being persisted. */
  savingAvatar: boolean;
  onPickFile: (file: File) => void;
  /** Re-open the crop editor for the picture already chosen. */
  onAdjust: () => void;
  onRemove: () => void;
};

/**
 * Profile-picture field: the circular preview plus its actions. The crop
 * controls deliberately live in a modal (opened automatically after a new
 * photo is picked, or via "Adjust") rather than sitting on the page — you only
 * need them when you are actually changing the picture.
 */
export function AvatarField({
  username,
  fullName,
  avatarUrl,
  crop,
  uploading,
  savingAvatar,
  onPickFile,
  onAdjust,
  onRemove,
}: AvatarFieldProps) {
  const { dict } = useI18n();
  const t = dict.settingsProfile;
  const fileInputRef = useRef<HTMLInputElement>(null);

  function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Reset so re-picking the same file fires onChange again.
    event.target.value = "";
    if (file) {
      onPickFile(file);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Label>{t.pictureLabel}</Label>

      <UserAvatar
        username={username}
        fullName={fullName}
        avatarUrl={avatarUrl}
        crop={crop}
        className="size-40"
        fallbackClassName="text-4xl"
      />

      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={onFileChange}
      />
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="secondary"
          onPress={() => fileInputRef.current?.click()}
          isPending={uploading}
          isDisabled={savingAvatar}
        >
          <FiCamera aria-hidden />
          {uploading ? t.uploading : t.pictureEdit}
        </Button>
        {avatarUrl ? (
          <Button
            size="sm"
            variant="tertiary"
            onPress={onAdjust}
            isDisabled={savingAvatar}
          >
            <FiCrop aria-hidden />
            {t.pictureAdjustButton}
          </Button>
        ) : null}
        {savingAvatar ? (
          <span className="text-xs text-muted">{t.saving}</span>
        ) : null}
      </div>
      {avatarUrl && !savingAvatar ? (
        <button
          type="button"
          onClick={onRemove}
          className="self-start text-xs text-muted hover:text-danger"
        >
          {t.pictureRemove}
        </button>
      ) : null}

      <p className="text-xs leading-relaxed text-muted">{t.pictureHint}</p>
    </div>
  );
}
