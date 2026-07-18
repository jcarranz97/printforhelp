import { Avatar } from "@heroui/react";

/** Build up-to-two-letter initials from a display name, falling back to the
 * username (e.g. "Oriana Moreno" -> "OM", "oriana-print" -> "OR"). */
function initialsFrom(fullName: string | null, username: string): string {
  const base = (fullName?.trim() || username).trim();
  const parts = base.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return base.slice(0, 2).toUpperCase();
}

type UserAvatarProps = {
  username: string;
  fullName?: string | null;
  avatarUrl?: string | null;
  /** HeroUI preset size; omit and use `className` for arbitrary sizes. */
  size?: "sm" | "md" | "lg";
  className?: string;
  /** Extra classes for the initials fallback (e.g. a larger font). */
  fallbackClassName?: string;
};

/**
 * A user's circular avatar, shared everywhere a user appears (top nav,
 * notifications, profile, settings). Renders the uploaded picture when set and
 * falls back to the user's initials otherwise. Built on the HeroUI `Avatar`.
 */
export function UserAvatar({
  username,
  fullName = null,
  avatarUrl = null,
  size,
  className,
  fallbackClassName,
}: UserAvatarProps) {
  // A hairline ring keeps the avatar readable when the uploaded picture's
  // edges match the page background (it would otherwise dissolve into it).
  const classes = ["ring-1 ring-[color:var(--border)]", className]
    .filter(Boolean)
    .join(" ");

  return (
    <Avatar color="accent" variant="soft" size={size} className={classes}>
      {avatarUrl ? (
        <Avatar.Image src={avatarUrl} alt={fullName ?? username} />
      ) : null}
      <Avatar.Fallback className={fallbackClassName}>
        {initialsFrom(fullName, username)}
      </Avatar.Fallback>
    </Avatar>
  );
}
