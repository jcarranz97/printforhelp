"use client";

import { Alert, AlertDialog, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { confirmReceivedAction } from "@/actions/tracking.action";
import { useI18n } from "@/i18n/provider";

/**
 * "Received at the center" action on a public tracking page.
 *
 * Rendered only when the backend says this viewer may confirm receipt (an
 * effective member of the drop-off center, or a maintainer/admin) and the
 * units are not received yet. The center usually gets here by scanning the
 * package's QR, which is the moment it can honestly say the aid arrived —
 * frequently on units the maker never advanced past "printed".
 *
 * Receipt cannot be undone from the UI, and it applies to the whole
 * contribution (every unit of the group, not just a scanned piece), so the
 * action is behind the same confirm dialog the maker's own advances use.
 */
export function ConfirmReceivedButton({
  trackingToken,
  quantity,
}: {
  trackingToken: string;
  quantity: number;
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-2">
      <AlertDialog>
        <Button size="sm">{t.markReceivedButton}</Button>
        <AlertDialog.Backdrop>
          <AlertDialog.Container placement="center">
            <AlertDialog.Dialog className="sm:max-w-[420px]">
              {({ close }) => (
                <>
                  <AlertDialog.CloseTrigger />
                  <AlertDialog.Header>
                    <AlertDialog.Icon status="success" />
                    <AlertDialog.Heading>
                      {t.markReceivedConfirmHeading}
                    </AlertDialog.Heading>
                  </AlertDialog.Header>
                  <AlertDialog.Body>
                    <p className="text-sm text-muted">
                      {t.markReceivedConfirmBody.replace(
                        "{count}",
                        String(quantity),
                      )}
                    </p>
                  </AlertDialog.Body>
                  <AlertDialog.Footer>
                    <Button slot="close" variant="tertiary">
                      {t.markReceivedCancel}
                    </Button>
                    <Button
                      isPending={pending}
                      onPress={() =>
                        startTransition(async () => {
                          const result =
                            await confirmReceivedAction(trackingToken);
                          setError(result.error);
                          if (!result.error) {
                            // Re-fetch so the status line updates and the
                            // button disappears.
                            router.refresh();
                          }
                          close();
                        })
                      }
                    >
                      {t.markReceivedButton}
                    </Button>
                  </AlertDialog.Footer>
                </>
              )}
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      </AlertDialog>

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
    </div>
  );
}
