"use client";

import { Alert, AlertDialog, Button } from "@heroui/react";
import { useState, useTransition } from "react";
import { FiX } from "react-icons/fi";

import {
  addContributorAction,
  removeContributorAction,
} from "@/actions/center-team.action";
import { ContributorPicker } from "@/components/centers/contributor-picker";
import { UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";
import type { CenterContributor } from "@/lib/collection-centers.api";

/**
 * The centre's team roster, shown to its effective owner.
 *
 * Being listed here is what lets someone act for the centre — create and pack
 * shipments, take delivery, dispatch. Without this panel the endpoints existed
 * but nobody could reach them, so a centre owner had no way to bring in help.
 *
 * Rows are deliberately compact — one line, avatar plus name, matching how a
 * person reads in the comment feed. Removing someone revokes their ability to
 * act for the centre, so it asks first rather than acting on a stray click.
 */
export function CenterTeam({
  centerId,
  contributors,
}: {
  centerId: string;
  contributors: CenterContributor[];
}) {
  const { dict } = useI18n();
  const t = dict.centerTeam;
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function add(username: string) {
    setError(null);
    startTransition(async () => {
      const res = await addContributorAction(centerId, username);
      if (res.error) {
        setError(res.error);
      }
    });
  }

  function remove(userId: string) {
    setError(null);
    startTransition(async () => {
      const res = await removeContributorAction(centerId, userId);
      if (res.error) {
        setError(res.error);
      }
    });
  }

  return (
    <section className="mt-10 flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-semibold">{t.title}</h2>
        <p className="text-sm text-muted">{t.subtitle}</p>
      </div>

      {contributors.length === 0 ? (
        <p className="text-sm text-muted">{t.empty}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-[var(--card-border)] rounded-lg border border-[var(--card-border)]">
          {contributors.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between gap-3 px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-2.5">
                <UserAvatar
                  username={c.username}
                  fullName={c.full_name}
                  avatarUrl={c.avatar_url}
                  crop={{
                    x: c.avatar_crop_x,
                    y: c.avatar_crop_y,
                    w: c.avatar_crop_w,
                    h: c.avatar_crop_h,
                  }}
                  size="sm"
                />
                <div className="flex min-w-0 flex-col leading-tight">
                  <span className="truncate text-sm font-medium">
                    {c.username}
                  </span>
                  {c.full_name && (
                    <span className="truncate text-xs text-muted">
                      {c.full_name}
                    </span>
                  )}
                </div>
              </div>

              <AlertDialog>
                <Button
                  variant="tertiary"
                  size="sm"
                  isIconOnly
                  aria-label={t.removeAria.replace("{username}", c.username)}
                  isPending={isPending}
                >
                  <FiX aria-hidden />
                </Button>
                <AlertDialog.Backdrop>
                  <AlertDialog.Container placement="center">
                    <AlertDialog.Dialog className="sm:max-w-[440px]">
                      {({ close }) => (
                        <>
                          <AlertDialog.CloseTrigger />
                          <AlertDialog.Header>
                            <AlertDialog.Icon status="warning" />
                            <AlertDialog.Heading>
                              {t.removeConfirmHeading}
                            </AlertDialog.Heading>
                          </AlertDialog.Header>
                          <AlertDialog.Body>
                            <p className="text-sm text-muted">
                              {t.removeConfirmBody.replace(
                                "{username}",
                                c.username,
                              )}
                            </p>
                          </AlertDialog.Body>
                          <AlertDialog.Footer>
                            <Button slot="close" variant="tertiary">
                              {t.removeConfirmCancel}
                            </Button>
                            <Button
                              variant="danger"
                              isPending={isPending}
                              onPress={() => {
                                remove(c.user_id);
                                close();
                              }}
                            >
                              {t.removeConfirmAccept}
                            </Button>
                          </AlertDialog.Footer>
                        </>
                      )}
                    </AlertDialog.Dialog>
                  </AlertDialog.Container>
                </AlertDialog.Backdrop>
              </AlertDialog>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-1">
        <ContributorPicker
          excludeUsernames={contributors.map((c) => c.username)}
          isPending={isPending}
          onSelect={add}
        />
      </div>

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
    </section>
  );
}
