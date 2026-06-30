"use client";

import { Alert, Button } from "@heroui/react";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useI18n } from "@/i18n/provider";
import {
  type Notice,
  type NoticeSeverity,
  type NoticeTranslation,
  resolveTranslation,
} from "@/lib/notices.api";

const DISMISS_KEY = "pforh_dismissed_notices";

// How long a notice stays on screen before it auto-hides for this page view.
// Auto-hide is temporary and is NOT remembered: the notice returns on the
// next page load. Only an explicit ✕ (persisted below) hides it for good.
const AUTO_HIDE_MS = 10000;

const SEVERITY_STATUS: Record<
  NoticeSeverity,
  "accent" | "success" | "warning" | "danger"
> = {
  info: "accent",
  success: "success",
  warning: "warning",
  critical: "danger",
};

/**
 * Per-severity emphasis layered on top of the HeroUI Alert so notices read
 * as prominent banners (a colored accent bar + tint) instead of plain cards.
 * Critical adds a heavier tint, ring, and shadow to demand attention.
 */
const SEVERITY_CLASS: Record<NoticeSeverity, string> = {
  info: "border-l-4 border-l-primary bg-primary/5",
  success: "border-l-4 border-l-success bg-success/10",
  warning: "border-l-4 border-l-warning bg-warning/10",
  critical:
    "border-l-4 border-l-danger bg-danger/15 ring-1 ring-danger/40 shadow-md",
};

const SEVERITY_BAR: Record<NoticeSeverity, string> = {
  info: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  critical: "bg-danger",
};

/** Map the current pathname to the page scope a notice may target. */
function pathToScope(pathname: string): string {
  if (pathname.startsWith("/centers")) {
    return "centers";
  }
  if (pathname.startsWith("/requests")) {
    return "requests";
  }
  if (pathname.startsWith("/parts")) {
    return "parts";
  }
  if (pathname.startsWith("/my-contributions")) {
    return "my_contributions";
  }
  if (pathname.startsWith("/about")) {
    return "about";
  }
  return "home";
}

type NoticeBannerProps = {
  notice: Notice;
  translation: NoticeTranslation;
  /** Run the auto-hide countdown (off when the notice is force-revealed). */
  countdown: boolean;
  /** Show the ✕ dismiss control (off for always-on entity notices). */
  dismissible: boolean;
  onExpire: (id: string) => void;
  onDismiss: (id: string) => void;
  dismissLabel: string;
};

/** A single banner with an auto-hide countdown that pauses on hover. */
function NoticeBanner({
  notice,
  translation,
  countdown,
  dismissible,
  onExpire,
  onDismiss,
  dismissLabel,
}: NoticeBannerProps) {
  const [paused, setPaused] = useState(false);
  const remainingRef = useRef(AUTO_HIDE_MS);
  const startRef = useRef(0);

  useEffect(() => {
    if (!countdown || paused) {
      return;
    }
    startRef.current = Date.now();
    const timer = setTimeout(() => onExpire(notice.id), remainingRef.current);
    return () => clearTimeout(timer);
  }, [countdown, paused, notice.id, onExpire]);

  function pause() {
    if (!countdown || paused) {
      return;
    }
    remainingRef.current = Math.max(
      0,
      remainingRef.current - (Date.now() - startRef.current),
    );
    setPaused(true);
  }

  function resume() {
    if (countdown) {
      setPaused(false);
    }
  }

  return (
    <div
      className="relative rounded-xl"
      onMouseEnter={pause}
      onMouseLeave={resume}
    >
      <Alert
        status={SEVERITY_STATUS[notice.severity]}
        className={`rounded-xl px-5 py-4 ${SEVERITY_CLASS[notice.severity]}`}
      >
        <Alert.Indicator className="[&_svg]:h-6 [&_svg]:w-6" />
        <Alert.Content className="gap-1">
          {translation.title && (
            <Alert.Title className="text-base font-bold sm:text-lg">
              {translation.title}
            </Alert.Title>
          )}
          <Alert.Description className="text-sm sm:text-[0.95rem]">
            {translation.message}
            {translation.action_url && translation.action_label && (
              <a
                href={translation.action_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block font-semibold underline underline-offset-2"
              >
                {translation.action_label} →
              </a>
            )}
          </Alert.Description>
        </Alert.Content>
        {dismissible && (
          <Button
            size="sm"
            variant="ghost"
            aria-label={dismissLabel}
            onPress={() => onDismiss(notice.id)}
          >
            ✕
          </Button>
        )}
      </Alert>
      {countdown && (
        <div className="absolute inset-x-0 bottom-0 h-1 overflow-hidden rounded-b-xl">
          <div
            className={`h-full origin-left opacity-40 ${SEVERITY_BAR[notice.severity]}`}
            style={{
              animation: `notice-countdown ${AUTO_HIDE_MS}ms linear forwards`,
              animationPlayState: paused ? "paused" : "running",
            }}
          />
        </div>
      )}
    </div>
  );
}

type NoticeBannerListProps = {
  notices: Notice[];
  /**
   * `"page"` filters by the current route against each notice's scopes;
   * `"entity"` shows every notice as-is (already scoped by the backend).
   */
  mode: "page" | "entity";
};

/**
 * Render a stack of notice banners. Each notice shows on every page load with
 * a countdown bar and auto-hides after a few seconds (not remembered). Only an
 * explicit ✕ persists in localStorage, hiding that notice across refreshes; a
 * "show hidden" toggle brings hidden notices back without a reload.
 */
export function NoticeBannerList({ notices, mode }: NoticeBannerListProps) {
  const { dict, locale } = useI18n();
  const t = dict.notices;
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [expired, setExpired] = useState<string[]>([]);
  // Notices explicitly brought back this session: shown without a countdown
  // and no longer treated as dismissed/expired.
  const [revealed, setRevealed] = useState<string[]>([]);

  useEffect(() => {
    setMounted(true);
    try {
      const raw = localStorage.getItem(DISMISS_KEY);
      if (raw) {
        setDismissed(JSON.parse(raw) as string[]);
      }
    } catch {
      // Ignore unavailable / malformed storage.
    }
  }, []);

  const dismiss = useCallback((id: string) => {
    setRevealed((prev) => prev.filter((x) => x !== id));
    setExpired((prev) => prev.filter((x) => x !== id));
    setDismissed((prev) => {
      const next = prev.includes(id) ? prev : [...prev, id];
      try {
        localStorage.setItem(DISMISS_KEY, JSON.stringify(next));
      } catch {
        // Ignore unavailable storage.
      }
      return next;
    });
  }, []);

  const expire = useCallback((id: string) => {
    setExpired((prev) => (prev.includes(id) ? prev : [...prev, id]));
  }, []);

  const scope = pathToScope(pathname);
  const applicable = notices.filter((notice) =>
    mode === "entity"
      ? true
      : notice.scopes.includes(scope) || notice.scopes.includes("all"),
  );

  if (applicable.length === 0) {
    return null;
  }

  const wrapperClass =
    mode === "page"
      ? "mx-auto flex max-w-5xl flex-col gap-2 px-4 py-3 sm:px-6"
      : "mt-6 flex flex-col gap-2";

  // Entity notices (on a part/center/request page) are intentional, approved
  // warnings: always shown, no countdown, and not dismissible. They render
  // server-side too since they do not depend on localStorage.
  if (mode === "entity") {
    return (
      <div className={wrapperClass}>
        {applicable.map((notice) => {
          const tr = resolveTranslation(notice, locale);
          if (!tr) {
            return null;
          }
          return (
            <NoticeBanner
              key={notice.id}
              notice={notice}
              translation={tr}
              countdown={false}
              dismissible={false}
              onExpire={expire}
              onDismiss={dismiss}
              dismissLabel={t.dismiss}
            />
          );
        })}
      </div>
    );
  }

  // Page banners: wait for the client to read persisted dismissals so a
  // dismissed notice never flashes before hydration hides it.
  if (!mounted) {
    return null;
  }

  const isHidden = (notice: Notice) =>
    !revealed.includes(notice.id) &&
    (dismissed.includes(notice.id) || expired.includes(notice.id));

  const hiddenIds = applicable.filter(isHidden).map((notice) => notice.id);
  const visible = applicable.filter((notice) => !isHidden(notice));

  /** Bring hidden notices back and forget any persisted ✕ for them. */
  function restore() {
    setRevealed((prev) => Array.from(new Set([...prev, ...hiddenIds])));
    setExpired((prev) => prev.filter((id) => !hiddenIds.includes(id)));
    setDismissed((prev) => {
      const next = prev.filter((id) => !hiddenIds.includes(id));
      try {
        localStorage.setItem(DISMISS_KEY, JSON.stringify(next));
      } catch {
        // Ignore unavailable storage.
      }
      return next;
    });
  }

  return (
    <div className={wrapperClass}>
      {visible.map((notice) => {
        const tr = resolveTranslation(notice, locale);
        if (!tr) {
          return null;
        }
        const countdown =
          !revealed.includes(notice.id) &&
          !dismissed.includes(notice.id) &&
          !expired.includes(notice.id);
        return (
          <NoticeBanner
            key={notice.id}
            notice={notice}
            translation={tr}
            countdown={countdown}
            dismissible
            onExpire={expire}
            onDismiss={dismiss}
            dismissLabel={t.dismiss}
          />
        );
      })}
      {hiddenIds.length > 0 && (
        <button
          type="button"
          onClick={restore}
          className="self-start text-xs text-muted hover:text-foreground hover:underline"
        >
          {t.showHidden} ({hiddenIds.length})
        </button>
      )}
    </div>
  );
}
