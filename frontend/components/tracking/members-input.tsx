"use client";

import { Chip } from "@heroui/react";
import { useEffect, useId, useState } from "react";
import { MdClose } from "react-icons/md";

import { searchUsersAction } from "@/actions/notifications.action";
import { useI18n } from "@/i18n/provider";
import type { UserSearchResult } from "@/lib/users.api";

/**
 * Username picker for the "group of users" visibility tier. Live-searches
 * real accounts (via the shared user-search action) and only lets the owner
 * add users that exist — unknown names are ignored server-side anyway.
 *
 * Selected usernames are mirrored to a hidden `name` field (comma-separated),
 * so it drops into the same form/action the plain tag input used.
 */
export function MembersInput({
  name,
  label,
  defaultMembers = [],
}: {
  name: string;
  label: string;
  defaultMembers?: string[];
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const inputId = useId();
  const [selected, setSelected] = useState<string[]>(defaultMembers);
  const [input, setInput] = useState("");
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<UserSearchResult[]>([]);

  // Debounced live search; an empty query still lists initial suggestions.
  useEffect(() => {
    if (!open) {
      return;
    }
    const handle = setTimeout(async () => {
      const users = await searchUsersAction(input.trim());
      setResults(users);
    }, 200);
    return () => clearTimeout(handle);
  }, [input, open]);

  function addUsername(username: string) {
    setSelected((current) =>
      current.some((s) => s.toLowerCase() === username.toLowerCase())
        ? current
        : [...current, username],
    );
    setInput("");
  }

  function removeUsername(username: string) {
    setSelected((current) => current.filter((s) => s !== username));
  }

  // Matching users not already selected.
  const matches = results.filter(
    (user) =>
      !selected.some((s) => s.toLowerCase() === user.username.toLowerCase()),
  );

  return (
    <div className="flex flex-col gap-1.5">
      <input type="hidden" name={name} value={selected.join(",")} />
      <label htmlFor={inputId} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <div className="relative">
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-[var(--card-border)] px-2 py-1.5">
          {selected.map((username) => (
            <Chip key={username} variant="soft" size="sm">
              {username}
              <button
                type="button"
                onClick={() => removeUsername(username)}
                aria-label={`${dict.tagInput.removeLabel} ${username}`}
                className="ml-1 inline-flex items-center text-muted hover:text-foreground"
              >
                <MdClose aria-hidden className="h-3 w-3" />
              </button>
            </Chip>
          ))}
          <input
            id={inputId}
            value={input}
            onChange={(event) => {
              setInput(event.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && matches.length > 0) {
                event.preventDefault();
                addUsername(matches[0].username);
              } else if (event.key === "Escape") {
                setOpen(false);
              } else if (
                event.key === "Backspace" &&
                input === "" &&
                selected.length > 0
              ) {
                removeUsername(selected[selected.length - 1]);
              }
            }}
            placeholder={t.membersSearchPlaceholder}
            className="min-w-28 flex-1 bg-transparent text-sm outline-none"
          />
        </div>

        {open && (
          <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-[var(--card-border)] bg-[var(--card)] py-1 shadow-lg">
            {matches.length === 0 ? (
              <li className="px-3 py-1.5 text-sm text-muted">
                {t.membersNoResults}
              </li>
            ) : (
              matches.map((user) => (
                <li key={user.id}>
                  {/* onMouseDown keeps the input from blurring before click. */}
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => addUsername(user.username)}
                    className="block w-full px-3 py-1.5 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10"
                  >
                    <span className="font-medium">{user.username}</span>
                    {user.full_name && (
                      <span className="ml-2 text-muted">{user.full_name}</span>
                    )}
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
