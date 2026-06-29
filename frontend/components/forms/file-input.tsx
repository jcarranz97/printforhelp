"use client";

import { Button } from "@heroui/react";
import { useRef, useState } from "react";

type FileInputProps = {
  /** Form field name — keeps the file in the surrounding form's submission. */
  name: string;
  accept?: string;
  chooseLabel: string;
  noFileLabel: string;
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
}: FileInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  return (
    <div className="flex items-center gap-3">
      <input
        ref={inputRef}
        type="file"
        name={name}
        accept={accept}
        className="hidden"
        onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
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
  );
}
