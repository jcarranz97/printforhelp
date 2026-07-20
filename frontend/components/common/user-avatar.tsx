import { Avatar } from "@heroui/react";

/**
 * The square region of a picture shown in the circular avatar, in percent of
 * the source image. Position (`x`/`y`) plus size (`w`/`h`) expresses both pan
 * and zoom, and being percentage-based it renders identically at every avatar
 * size. `w`/`h` of 100 means "no crop chosen".
 */
export type AvatarCrop = {
  x: number;
  y: number;
  w: number;
  h: number;
};

export const FULL_CROP: AvatarCrop = { x: 0, y: 0, w: 100, h: 100 };

/** True when the crop covers the whole image, i.e. the user never chose one. */
export function isFullCrop(crop: AvatarCrop): boolean {
  return crop.w >= 99.99 && crop.h >= 99.99;
}

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
  /** Which part of the picture to show; defaults to the whole image. */
  crop?: AvatarCrop;
  /** HeroUI preset size; omit and use `className` for arbitrary sizes. */
  size?: "sm" | "md" | "lg";
  className?: string;
  /** Extra classes for the initials fallback (e.g. a larger font). */
  fallbackClassName?: string;
};

/**
 * A user's circular avatar, shared everywhere a user appears (top nav,
 * notifications, profile, settings). Renders the uploaded picture cropped to
 * the user's chosen region, and falls back to their initials otherwise.
 */
export function UserAvatar({
  username,
  fullName = null,
  avatarUrl = null,
  crop = FULL_CROP,
  size,
  className,
  fallbackClassName,
}: UserAvatarProps) {
  // `rounded-full` is explicit: HeroUI's `.avatar` uses a *fixed* `rounded-3xl`
  // radius, which reads as a circle at nav size but as a rounded square once
  // the avatar is large (profile/settings). A hairline ring keeps the avatar
  // readable when the picture's edges match the page background.
  const classes = ["rounded-full ring-1 ring-[color:var(--border)]", className]
    .filter(Boolean)
    .join(" ");

  return (
    <Avatar color="accent" variant="soft" size={size} className={classes}>
      {avatarUrl ? (
        <CroppedImage src={avatarUrl} alt={fullName ?? username} crop={crop} />
      ) : null}
      <Avatar.Fallback
        className={["rounded-full", fallbackClassName]
          .filter(Boolean)
          .join(" ")}
      >
        {initialsFrom(fullName, username)}
      </Avatar.Fallback>
    </Avatar>
  );
}

/**
 * Render the crop region so it exactly fills the (square) avatar.
 *
 * Scale the image up so the crop's width/height become the container's, then
 * shift it so the crop's top-left lands at the container's top-left. Everything
 * is a percentage of the container, so no pixel measurements are needed and the
 * same numbers work at every avatar size.
 *
 * With no crop chosen we fall back to a plain centred `cover` fit, which is
 * also what keeps an avatar set through the API (no crop values) undistorted.
 */
function CroppedImage({
  src,
  alt,
  crop,
}: {
  src: string;
  alt: string;
  crop: AvatarCrop;
}) {
  if (isFullCrop(crop)) {
    return <Avatar.Image src={src} alt={alt} className="object-cover" />;
  }
  return (
    <Avatar.Image
      src={src}
      alt={alt}
      className="absolute max-w-none"
      style={{
        width: `${(100 / crop.w) * 100}%`,
        height: `${(100 / crop.h) * 100}%`,
        left: `${-(crop.x / crop.w) * 100}%`,
        top: `${-(crop.y / crop.h) * 100}%`,
      }}
    />
  );
}
