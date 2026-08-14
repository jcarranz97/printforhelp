"use client";

import { Alert, AlertDialog, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { setCenterListedAction } from "@/actions/collection-centers.action";
import { useI18n } from "@/i18n/provider";

/**
 * Hide a centre from the public directory, or put it back.
 *
 * Registering from `/centers` defaults a centre to listed, and people meaning
 * to create a private, request-specific drop-off routinely notice only
 * afterwards. Before this, the flag was create-time only and the only way out
 * was to archive and start again.
 *
 * Hiding is **not** a takedown, and the confirmation says so: the centre keeps
 * its page, its shipments and its history, and any link already shared still
 * resolves. Its own staff still reach it from "My centres". The real
 * authorization runs server-side (NFR-006); this button is UX only.
 */
export function CenterListedButton({
  centerId,
  listed,
}: {
  centerId: string;
  listed: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.centerListed;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function run(next: boolean) {
    setError(null);
    startTransition(async () => {
      const res = await setCenterListedAction(centerId, next);
      if (res.error) {
        setError(res.error);
        return;
      }
      router.refresh();
    });
  }

  // Publishing back is harmless and reversible, so it needs no confirmation.
  if (!listed) {
    return (
      <div className="flex flex-col items-start gap-2">
        <Button
          size="sm"
          variant="secondary"
          isPending={isPending}
          onPress={() => run(true)}
        >
          {t.makePublic}
        </Button>
        {error && <Failure message={error} />}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <AlertDialog>
        <Button size="sm" variant="secondary" isPending={isPending}>
          {t.makePrivate}
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
                      {t.confirmHeading}
                    </AlertDialog.Heading>
                  </AlertDialog.Header>
                  <AlertDialog.Body>
                    <p className="text-sm text-muted">{t.confirmBody}</p>
                  </AlertDialog.Body>
                  <AlertDialog.Footer>
                    <Button slot="close" variant="tertiary">
                      {t.confirmCancel}
                    </Button>
                    <Button
                      isPending={isPending}
                      onPress={() => {
                        run(false);
                        close();
                      }}
                    >
                      {t.confirmAccept}
                    </Button>
                  </AlertDialog.Footer>
                </>
              )}
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      </AlertDialog>
      {error && <Failure message={error} />}
    </div>
  );
}

function Failure({ message }: { message: string }) {
  return (
    <Alert status="danger">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Description>{message}</Alert.Description>
      </Alert.Content>
    </Alert>
  );
}
