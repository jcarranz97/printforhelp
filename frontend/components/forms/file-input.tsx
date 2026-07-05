"use client";

import { Button } from "@heroui/react";
import { useEffect, useRef, useState } from "react";

type FileInputProps = {
  /** Form field name — keeps the file in the surrounding form's submission. */
  name: string;
  accept?: string;
  chooseLabel: string;
  noFileLabel: string;
  /**
   * When true, render a thumbnail of the chosen file if it is an image, so
   * the user can confirm they picked the right one before submitting. The
   * preview is a local object URL — no upload happens until the form is sent.
   */
  preview?: boolean;
};

/**
 * A styled file picker: a HeroUI Button that opens a hidden native
 * `<input type="file">`. The input stays in the DOM with its `name` so it
 * still submits with the surrounding `<form>` (server actions read it from
 * FormData); the chosen filename is shown next to the button.
 */
export function FileInput({
  name,
  accept,
  chooseLabel,
  noFileLabel,
  preview = false,
}: FileInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Release the object URL when it is replaced or the component unmounts,
  // so selecting several files in a row does not leak blobs.
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  function onChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setFileName(file?.name ?? null);
    setPreviewUrl(
      preview && file && file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : null,
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          name={name}
          accept={accept}
          className="hidden"
          onChange={onChange}
        />
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onPress={() => inputRef.current?.click()}
        >
          {chooseLabel}
        </Button>
        <span className="truncate text-sm text-muted">
          {fileName ?? noFileLabel}
        </span>
      </div>
      {previewUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={previewUrl}
          alt={fileName ?? ""}
          className="h-24 w-24 rounded-md border border-default-200 object-cover"
        />
      )}
    </div>
  );
}
