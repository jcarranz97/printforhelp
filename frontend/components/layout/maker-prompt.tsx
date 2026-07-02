"use client";

import { Button, Modal } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { setMakerFlagAction } from "@/actions/flags.action";
import { useI18n } from "@/i18n/provider";

const SESSION_KEY = "pforh_maker_prompt_dismissed";

/**
 * One-time modal asking a logged-in user whether they are a maker (they 3D
 * print to help). Rendered by the root layout only when the `maker` flag is
 * unknown. "Yes"/"No" persist the answer (never asked again); "Ask later" just
 * closes it for this browser session (it stays unknown, so it asks again next
 * session). Mirrors the LocaleToast one-time-prompt pattern.
 */
export function MakerPrompt() {
  const { dict } = useI18n();
  const t = dict.makerPrompt;
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [isPending, startTransition] = useTransition();

  // Only open if the user hasn't chosen "ask later" this session.
  useEffect(() => {
    if (sessionStorage.getItem(SESSION_KEY) !== "1") {
      setIsOpen(true);
    }
  }, []);

  function answer(value: boolean) {
    startTransition(async () => {
      await setMakerFlagAction(value);
      setIsOpen(false);
      router.refresh();
    });
  }

  function askLater() {
    sessionStorage.setItem(SESSION_KEY, "1");
    setIsOpen(false);
  }

  return (
    <Modal.Backdrop
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open) {
          askLater();
        }
      }}
    >
      <Modal.Container>
        <Modal.Dialog className="sm:max-w-[380px]">
          <Modal.Header>
            <Modal.Heading>{t.title}</Modal.Heading>
          </Modal.Header>
          <Modal.Body>
            <p>{t.question}</p>
          </Modal.Body>
          <Modal.Footer className="flex-col-reverse sm:flex-row sm:justify-end">
            <Button
              variant="tertiary"
              isDisabled={isPending}
              onPress={askLater}
            >
              {t.later}
            </Button>
            <Button
              variant="secondary"
              isDisabled={isPending}
              onPress={() => answer(false)}
            >
              {t.no}
            </Button>
            <Button isPending={isPending} onPress={() => answer(true)}>
              {t.yes}
            </Button>
          </Modal.Footer>
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  );
}
