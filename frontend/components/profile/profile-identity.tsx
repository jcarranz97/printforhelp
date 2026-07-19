"use client";

import {
  Button,
  Input,
  Label,
  TextArea,
  TextField,
  toast,
} from "@heroui/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { FiCamera } from "react-icons/fi";

import { updateProfileAction } from "@/actions/profile.action";
import { UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";
import type { PublicProfileUser } from "@/lib/users.api";

const BIO_MAX = 280;

type ProfileIdentityProps = {
  user: PublicProfileUser;
  isOwner: boolean;
  /** Rendered under the edit controls — "Joined <date>". */
  memberSince: string;
};

/**
 * The left-hand identity column: avatar, name, handle, bio.
 *
 * For the owner it doubles as the editor. "Edit profile" swaps the name and
 * bio for inputs **in place** rather than navigating away, so the change is
 * made where its result is visible. The picture is the one thing that still
 * links out to settings: cropping needs a modal and more room than this
 * column has.
 */
export function ProfileIdentity({
  user,
  isOwner,
  memberSince,
}: ProfileIdentityProps) {
  const { dict } = useI18n();
  const t = dict.profile;
  const ts = dict.settingsProfile;
  const router = useRouter();

  const [editing, setEditing] = useState(false);
  const [fullName, setFullName] = useState(user.full_name ?? "");
  const [bio, setBio] = useState(user.bio ?? "");
  const [isSaving, startSaving] = useTransition();

  const displayName = user.full_name?.trim() || user.username;
  const crop = {
    x: user.avatar_crop_x,
    y: user.avatar_crop_y,
    w: user.avatar_crop_w,
    h: user.avatar_crop_h,
  };

  function cancel() {
    // Drop the edits and go back to what is actually saved.
    setFullName(user.full_name ?? "");
    setBio(user.bio ?? "");
    setEditing(false);
  }

  function save() {
    startSaving(async () => {
      const result = await updateProfileAction({
        full_name: fullName.trim() || null,
        bio: bio.trim() || null,
      });
      if (result.ok) {
        setEditing(false);
        toast.success(ts.saved);
        // The header greeting reads the same fields, so refresh the tree.
        router.refresh();
      } else {
        toast.danger(ts.errorGeneric);
      }
    });
  }

  const avatar = (
    <UserAvatar
      username={user.username}
      fullName={user.full_name}
      avatarUrl={user.avatar_url}
      crop={crop}
      className="size-40 md:size-56"
      fallbackClassName="text-5xl md:text-6xl"
    />
  );

  return (
    <aside className="flex flex-col gap-4">
      {isOwner ? (
        // The picture is its own editor entry point (GitHub does the same):
        // it needs the crop modal, which lives in settings.
        <Link
          href="/settings/profile"
          aria-label={t.changePicture}
          title={t.changePicture}
          className="group relative self-start rounded-full"
        >
          {avatar}
          <span className="absolute bottom-2 right-2 flex size-9 items-center justify-center rounded-full border border-border bg-background text-muted shadow-sm transition-colors group-hover:text-foreground">
            <FiCamera className="size-4" aria-hidden />
          </span>
        </Link>
      ) : (
        <div className="self-start">{avatar}</div>
      )}

      {editing ? (
        <div className="flex flex-col gap-4">
          <TextField value={fullName} onChange={setFullName} maxLength={255}>
            <Label className="text-sm font-semibold">{ts.nameLabel}</Label>
            <Input />
          </TextField>

          <div className="flex flex-col gap-1.5">
            <Label className="text-sm font-semibold">{ts.bioLabel}</Label>
            <TextArea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={BIO_MAX}
              rows={3}
              fullWidth
              placeholder={ts.bioPlaceholder}
              style={{ resize: "vertical" }}
            />
            <span className="self-end text-xs text-muted">
              {bio.length} / {BIO_MAX}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button size="sm" onPress={save} isPending={isSaving}>
              {isSaving ? ts.saving : t.editSave}
            </Button>
            <Button
              size="sm"
              variant="tertiary"
              onPress={cancel}
              isDisabled={isSaving}
            >
              {t.editCancel}
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="flex flex-col">
            <h1 className="text-2xl font-bold leading-tight">{displayName}</h1>
            {user.full_name?.trim() ? (
              <span className="text-lg text-muted">{user.username}</span>
            ) : null}
          </div>
          {user.bio?.trim() ? (
            <p className="text-sm leading-relaxed text-foreground/80">
              {user.bio}
            </p>
          ) : null}
          {isOwner ? (
            <Button
              size="sm"
              variant="secondary"
              fullWidth
              onPress={() => setEditing(true)}
            >
              {t.editProfile}
            </Button>
          ) : null}
        </>
      )}

      <p className="text-xs text-muted">{memberSince}</p>
    </aside>
  );
}
