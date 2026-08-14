"use client";

import { Button, Input, Label, TextField } from "@heroui/react";
import { useEffect, useRef, useState } from "react";

import { searchUsersAction } from "@/actions/notifications.action";
import { UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";
import type { UserSearchResult } from "@/lib/users.api";

/**
 * Typeahead for picking the person to add to a centre's team.
 *
 * Nobody knows a collaborator's exact username, so this searches as you type
 * and requires a **selection** rather than accepting free text — the backend
 * matches on the exact username, and a near miss would just be a confusing
 * "user not found". Reuses the same debounced `searchUsersAction` the @mention
 * composer uses, so there is one user-search path in the product.
 */
export function ContributorPicker({
  excludeUsernames,
  isPending,
  onSelect,
}: {
  /** Already on the team — shown greyed rather than hidden, so it is obvious
   *  why someone you searched for cannot be picked. */
  excludeUsernames: string[];
  isPending: boolean;
  onSelect: (username: string) => void;
}) {
  const { dict } = useI18n();
  const t = dict.centerTeam;
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [chosen, setChosen] = useState<UserSearchResult | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const already = new Set(excludeUsernames.map((u) => u.toLowerCase()));

  // Debounced search. A blank query returns nothing, so the menu only opens
  // once there is something to match on.
  useEffect(() => {
    if (chosen !== null || query.trim().length === 0) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const id = setTimeout(async () => {
      const users = await searchUsersAction(query.trim());
      if (!cancelled) {
        setResults(users);
        setActiveIndex(0);
        setLoading(false);
        setOpen(true);
      }
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [query, chosen]);

  // Close on an outside click, like any other menu.
  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!boxRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const selectable = results.filter(
    (u) => !already.has(u.username.toLowerCase()),
  );

  function choose(user: UserSearchResult) {
    if (already.has(user.username.toLowerCase())) {
      return;
    }
    setChosen(user);
    setQuery(user.username);
    setOpen(false);
  }

  function reset() {
    setChosen(null);
    setQuery("");
    setResults([]);
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (!open || selectable.length === 0) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => (i + 1) % selectable.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => (i - 1 + selectable.length) % selectable.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(selectable[activeIndex]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-end gap-2">
        <div ref={boxRef} className="relative w-full max-w-xs">
          <TextField
            value={query}
            onChange={(value) => {
              setQuery(value);
              // Typing after picking someone invalidates the selection.
              if (chosen) {
                setChosen(null);
              }
            }}
            aria-label={t.addLabel}
          >
            <Label>{t.addLabel}</Label>
            <Input
              placeholder={t.addPlaceholder}
              onKeyDown={onKeyDown}
              autoComplete="off"
            />
          </TextField>

          {open && !chosen && query.trim().length > 0 && (
            <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-default-200 bg-background shadow-lg">
              {loading && selectable.length === 0 && (
                <li className="px-3 py-2 text-sm text-muted">{t.searching}</li>
              )}
              {!loading && results.length === 0 && (
                <li className="px-3 py-2 text-sm text-muted">{t.noMatches}</li>
              )}
              {results.map((user) => {
                const taken = already.has(user.username.toLowerCase());
                const index = selectable.indexOf(user);
                return (
                  <li key={user.id}>
                    <button
                      type="button"
                      disabled={taken}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        choose(user);
                      }}
                      className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm ${
                        taken
                          ? "cursor-not-allowed opacity-50"
                          : index === activeIndex
                            ? "bg-default-100"
                            : "hover:bg-default-100"
                      }`}
                    >
                      <UserAvatar
                        username={user.username}
                        fullName={user.full_name}
                        avatarUrl={user.avatar_url}
                        crop={{
                          x: user.avatar_crop_x,
                          y: user.avatar_crop_y,
                          w: user.avatar_crop_w,
                          h: user.avatar_crop_h,
                        }}
                        size="sm"
                      />
                      <span className="flex min-w-0 flex-col leading-tight">
                        <span className="truncate font-medium">
                          {user.username}
                        </span>
                        {user.full_name && (
                          <span className="truncate text-xs text-muted">
                            {user.full_name}
                          </span>
                        )}
                        {taken && (
                          <span className="text-xs text-muted">
                            {t.alreadyOnTeam}
                          </span>
                        )}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <Button
          isPending={isPending}
          isDisabled={chosen === null}
          onPress={() => {
            if (chosen) {
              onSelect(chosen.username);
              reset();
            }
          }}
        >
          {t.add}
        </Button>
      </div>
      <p className="text-xs text-muted">{t.addHint}</p>
    </div>
  );
}
