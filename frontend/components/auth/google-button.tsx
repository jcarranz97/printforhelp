"use client";

import { Alert } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { googleLoginAction } from "@/actions/auth.action";
import { useI18n } from "@/i18n/provider";

const GSI_SRC = "https://accounts.google.com/gsi/client";

/** Minimal shape of the Google Identity Services API we use. */
type GoogleCredentialResponse = { credential?: string };
type GoogleId = {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
  }) => void;
  renderButton: (
    parent: HTMLElement,
    options: Record<string, string | number>,
  ) => void;
};
type WindowWithGoogle = Window & {
  google?: { accounts: { id: GoogleId } };
};

/** Load the GIS script once and resolve when it is ready. */
function loadGsiScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GSI_SRC}"]`,
    );
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = GSI_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google script"));
    document.head.appendChild(script);
  });
}

export function GoogleButton() {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const { dict, locale } = useI18n();
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clientId || !containerRef.current) {
      return;
    }
    let cancelled = false;

    void loadGsiScript().then(() => {
      const win = window as WindowWithGoogle;
      if (cancelled || !win.google || !containerRef.current) {
        return;
      }
      win.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          const result = await googleLoginAction(response.credential ?? "");
          if (result.error) {
            setError(result.error);
            return;
          }
          router.refresh();
          router.push("/");
        },
      });
      win.google.accounts.id.renderButton(containerRef.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        width: 320,
        locale,
      });
    });

    return () => {
      cancelled = true;
    };
  }, [clientId, locale, router]);

  if (!clientId) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3">
      <div ref={containerRef} className="flex justify-center" />
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
