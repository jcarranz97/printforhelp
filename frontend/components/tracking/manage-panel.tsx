"use client";

import { Alert, AlertDialog, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { adjustQuantityAction } from "@/actions/tracking.action";
import { QrBundleDownloads } from "@/components/tracking/qr-bundle-downloads";
import { useI18n } from "@/i18n/provider";
import type { ContributorMessage } from "@/lib/tracking.api";

/**
 * Maintainer/admin controls on the public tracking page.
 *
 * Makers commit to a number before they print and the box that reaches the
 * center routinely holds a different one — 283 promised, 300 delivered. The
 * maker's own edit is locked by then (`delivered` onwards), so the correction
 * has to happen here, on the page the center already has open after scanning.
 *
 * The two halves are deliberately adjacent: raising the count mints QRs only
 * for the new trailing units, and the reprint range right below is how the
 * maintainer gets *just those* on paper.
 */
export function TrackingManagePanel({
  trackingToken,
  groupId,
  quantity,
  trackedUnits,
  hasLabel,
  savedMessages,
}: {
  trackingToken: string;
  groupId: string;
  quantity: number;
  trackedUnits: number;
  hasLabel: boolean;
  savedMessages: ContributorMessage[];
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const router = useRouter();

  const [value, setValue] = useState(String(quantity));
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  // The units a correction just added — nothing has been printed for them, so
  // they become the preselected reprint window below.
  const [added, setAdded] = useState<{ from: number; to: number } | null>(null);
  const [pending, startTransition] = useTransition();

  const parsed = Number(value);
  const isValid = Number.isInteger(parsed) && parsed >= 1;
  const changed = isValid && parsed !== quantity;
  // Only a shrink destroys anything, so only a shrink is worth interrupting.
  const isShrink = changed && parsed < quantity;
  const retiredCount = isShrink ? trackedUnits - parsed : 0;

  function submit() {
    // Captured before the refresh swaps the props out from under us.
    const printedUpTo = trackedUnits;
    startTransition(async () => {
      const result = await adjustQuantityAction(trackingToken, parsed);
      setError(result.error);
      setSaved(!result.error);
      if (result.error) {
        return;
      }
      // Trust the server's unit count, not the requested quantity: it is
      // clamped at the per-contribution tracking cap.
      const now = result.trackedUnits ?? printedUpTo;
      // A shrink adds nothing to print, so it clears any stale window.
      setAdded(now > printedUpTo ? { from: printedUpTo + 1, to: now } : null);
      router.refresh();
    });
  }

  return (
    <section className="mt-8 flex flex-col gap-5 rounded-xl border border-[var(--card-border)] bg-default-50 p-5">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">{t.managePanelTitle}</h2>
        <p className="text-sm text-muted">{t.managePanelHint}</p>
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor="manage_quantity" className="text-sm font-medium">
          {t.quantityLabel}
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <input
            id="manage_quantity"
            type="number"
            min={1}
            inputMode="numeric"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setSaved(false);
              setError(null);
            }}
            className="w-32 rounded-lg border border-[var(--card-border)] bg-transparent px-3 py-2 text-sm outline-none"
          />

          {isShrink ? (
            <AlertDialog>
              <Button variant="secondary" size="sm" isPending={pending}>
                {t.quantitySave}
              </Button>
              <AlertDialog.Backdrop>
                <AlertDialog.Container placement="center">
                  <AlertDialog.Dialog className="sm:max-w-[460px]">
                    {({ close }) => (
                      <>
                        <AlertDialog.CloseTrigger />
                        <AlertDialog.Header>
                          <AlertDialog.Icon status="warning" />
                          <AlertDialog.Heading>
                            {t.shrinkConfirmHeading}
                          </AlertDialog.Heading>
                        </AlertDialog.Header>
                        <AlertDialog.Body>
                          <p className="text-sm text-muted">
                            {t.shrinkConfirmBody
                              .replace("{from}", String(quantity))
                              .replace("{to}", String(parsed))
                              .replace("{count}", String(retiredCount))
                              .replace("{first}", String(parsed + 1))
                              .replace("{last}", String(trackedUnits))}
                          </p>
                        </AlertDialog.Body>
                        <AlertDialog.Footer>
                          <Button slot="close" variant="tertiary">
                            {t.shrinkConfirmCancel}
                          </Button>
                          <Button
                            variant="danger"
                            isPending={pending}
                            onPress={() => {
                              submit();
                              close();
                            }}
                          >
                            {t.shrinkConfirmAccept}
                          </Button>
                        </AlertDialog.Footer>
                      </>
                    )}
                  </AlertDialog.Dialog>
                </AlertDialog.Container>
              </AlertDialog.Backdrop>
            </AlertDialog>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              isPending={pending}
              isDisabled={!changed}
              onPress={submit}
            >
              {t.quantitySave}
            </Button>
          )}
        </div>

        <p className="text-xs text-muted">{t.quantityHelp}</p>

        {/* Tell the maintainer up front which labels they will need, since
            the reprint range below is the next thing they touch. */}
        {changed && !isShrink && (
          <p className="text-xs text-[var(--accent-strong)]">
            {t.growNotice
              .replace("{first}", String(trackedUnits + 1))
              .replace("{last}", String(parsed))}
          </p>
        )}
        {!isValid && value.trim() !== "" && (
          <p className="text-xs text-danger">{t.errorInvalidQuantity}</p>
        )}
        {saved && (
          <Alert status="success">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>
                {added
                  ? t.quantitySavedReprint
                      .replace("{first}", String(added.from))
                      .replace("{last}", String(added.to))
                  : t.quantitySaved}
              </Alert.Description>
            </Alert.Content>
          </Alert>
        )}
        {error && (
          <Alert status="danger">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </div>

      <div className="flex flex-col gap-3 border-t border-[var(--card-border)] pt-5">
        <h3 className="text-sm font-semibold">{t.reprintTitle}</h3>
        <p className="text-xs text-muted">{t.reprintHint}</p>
        <QrBundleDownloads
          groupId={groupId}
          hasLabel={hasLabel}
          savedMessages={savedMessages}
          totalUnits={trackedUnits}
          suggestedFrom={added?.from}
          suggestedTo={added?.to}
          makerMessageNotice
          // A reprint is almost always "the units I just added": the group QR
          // went out with the first batch and does not need reprinting.
          defaultScope="individual"
        />
      </div>
    </section>
  );
}
