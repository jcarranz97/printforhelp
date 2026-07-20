"use client";

import { Button, Dropdown, type Key, Label, Separator } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { FiLogOut, FiSettings, FiUser } from "react-icons/fi";

import { logoutAction } from "@/actions/auth.action";
import { type AvatarCrop, UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";
import { profilePath } from "@/lib/profile-href";

type UserMenuProps = {
  username: string;
  fullName: string | null;
  avatarUrl: string | null;
  crop: AvatarCrop;
};

/**
 * The account menu in the top nav (GitHub-style): the user's avatar opens a
 * dropdown headed by their identity, with links to their public profile and
 * settings, and "Log out" as the last item.
 */
export function UserMenu({
  username,
  fullName,
  avatarUrl,
  crop,
}: UserMenuProps) {
  const { dict } = useI18n();
  const t = dict.header;
  const router = useRouter();
  const [, startTransition] = useTransition();

  function onAction(key: Key) {
    if (key === "profile") {
      router.push(profilePath(username));
    } else if (key === "settings") {
      router.push("/settings/profile");
    } else if (key === "logout") {
      startTransition(async () => {
        await logoutAction();
      });
    }
  }

  return (
    <Dropdown>
      <Button
        isIconOnly
        size="sm"
        variant="ghost"
        aria-label={t.userMenuAriaLabel}
        className="min-h-11 min-w-11 rounded-full p-0 sm:min-h-9 sm:min-w-9"
      >
        <UserAvatar
          username={username}
          fullName={fullName}
          avatarUrl={avatarUrl}
          crop={crop}
          size="sm"
        />
      </Button>
      <Dropdown.Popover className="min-w-[240px]">
        <div className="flex items-center gap-3 px-3 py-2.5">
          <UserAvatar
            username={username}
            fullName={fullName}
            avatarUrl={avatarUrl}
            size="sm"
          />
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-semibold">{username}</span>
            {fullName ? (
              <span className="truncate text-xs text-muted">{fullName}</span>
            ) : null}
          </div>
        </div>
        <Separator />
        <Dropdown.Menu onAction={onAction}>
          <Dropdown.Item id="profile" textValue={t.profile}>
            <FiUser aria-hidden />
            <Label>{t.profile}</Label>
          </Dropdown.Item>
          <Dropdown.Item id="settings" textValue={t.settings}>
            <FiSettings aria-hidden />
            <Label>{t.settings}</Label>
          </Dropdown.Item>
          <Separator />
          <Dropdown.Item id="logout" textValue={t.logout}>
            <FiLogOut aria-hidden />
            <Label>{t.logout}</Label>
          </Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
