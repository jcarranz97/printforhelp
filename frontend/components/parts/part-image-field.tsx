"use client";

import { Button, Input, Label, TextField } from "@heroui/react";
import { useEffect, useRef, useState } from "react";

import { useI18n } from "@/i18n/provider";

/**
 * Aspect ratio (width / height) of a Part image. Shared between this picker
 * and the actual render (part detail + catalog cards) so the crop box shown
 * here matches what the pages display. Exported as a CSS string too. Parts
 * use a taller 4:3 frame than the request cover banner (24:9).
 */
export const PART_IMAGE_ASPECT = 4 / 3;
export const PART_IMAGE_ASPECT_CSS = "4 / 3";

type PartImageFieldProps = {
  /** Existing image URL (edit form); pre-fills the URL field + preview. */
  defaultUrl?: string;
  /** Saved focal point (percent, 0-100); defaults to the center. */
  defaultFocusX?: number;
  defaultFocusY?: number;
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));
const round1 = (value: number) => Math.round(value * 10) / 10;

/**
 * Size of the visible crop box, as a percentage of the displayed image. The
 * image covers its box, so one axis is fully shown and the other is cropped:
 * whichever axis is "too long" relative to the frame ratio is the one that
 * shrinks.
 */
function cropSizePercent(imgAspect: number): { w: number; h: number } {
  if (imgAspect <= PART_IMAGE_ASPECT) {
    // Image is narrower/taller than the frame -> full width, cropped height.
    return { w: 100, h: (imgAspect / PART_IMAGE_ASPECT) * 100 };
  }
  // Image is wider than the frame -> full height, cropped width.
  return { w: (PART_IMAGE_ASPECT / imgAspect) * 100, h: 100 };
}

/**
 * Image field for a Part: pick/upload a file or paste a URL, then drag a box
 * over the image to choose which part shows in the fixed 4:3 frame (the
 * dimmed area is cropped out). The chosen frame is stored as a focal point
 * (CSS `object-position`). Submits `image_file` (the chosen file),
 * `image_url` (pasted/existing), and `image_focus_x` / `image_focus_y`
 * (percent) so the server action can resolve and store them.
 */
export function PartImageField({
  defaultUrl = "",
  defaultFocusX = 50,
  defaultFocusY = 50,
}: PartImageFieldProps) {
  const { dict } = useI18n();
  const t = dict.partForm;

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pickerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [url, setUrl] = useState(defaultUrl);
  const [imgAspect, setImgAspect] = useState<number | null>(null);
  const [focusX, setFocusX] = useState(defaultFocusX);
  const [focusY, setFocusY] = useState(defaultFocusY);

  // The image shown: a freshly picked file wins, else the pasted/existing URL.
  const src = objectUrl ?? (url.trim() || null);

  // Release the object URL when it is replaced or on unmount.
  useEffect(() => {
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [objectUrl]);

  function onPickFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setFileName(file?.name ?? null);
    setImgAspect(null);
    setObjectUrl(file ? URL.createObjectURL(file) : null);
  }

  const crop = imgAspect ? cropSizePercent(imgAspect) : null;

  // Drag the crop box: treat the pointer as the box center, clamped so the
  // box stays inside the image, then map its offset back to a 0-100 focus.
  function setFocusFromEvent(clientX: number, clientY: number) {
    const el = pickerRef.current;
    if (!el || !crop) {
      return;
    }
    const rect = el.getBoundingClientRect();
    const cx = clamp(((clientX - rect.left) / rect.width) * 100, 0, 100);
    const cy = clamp(((clientY - rect.top) / rect.height) * 100, 0, 100);
    const freeW = 100 - crop.w;
    const freeH = 100 - crop.h;
    const left = clamp(cx - crop.w / 2, 0, freeW);
    const top = clamp(cy - crop.h / 2, 0, freeH);
    setFocusX(freeW > 0 ? round1((left / freeW) * 100) : 50);
    setFocusY(freeH > 0 ? round1((top / freeH) * 100) : 50);
  }

  const cropLeft = crop ? ((100 - crop.w) * focusX) / 100 : 0;
  const cropTop = crop ? ((100 - crop.h) * focusY) / 100 : 0;

  return (
    <div className="flex flex-col gap-3">
      <span className="text-sm font-medium">{t.imageUpload}</span>
      <div className="flex items-center gap-3">
        <input
          ref={fileInputRef}
          type="file"
          name="image_file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={onPickFile}
        />
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onPress={() => fileInputRef.current?.click()}
        >
          {t.chooseFile}
        </Button>
        <span className="truncate text-sm text-muted">
          {fileName ?? t.noFile}
        </span>
      </div>
      <span className="text-xs text-muted">
        {t.imageUploadHint} {t.imageSizeHint}
      </span>

      {/* type="text", not "url": our own uploads yield a relative /media path,
          which native url validation would reject and block submission. */}
      <TextField name="image_url" type="text" value={url} onChange={setUrl}>
        <Label>{t.image}</Label>
        <Input placeholder={t.imagePlaceholder} />
      </TextField>

      {src && (
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium">{t.focusLabel}</span>
          <span className="text-xs text-muted">{t.focusHelp}</span>
          <div
            ref={pickerRef}
            className="relative inline-block max-w-full touch-none select-none self-start overflow-hidden rounded-lg border border-default-200"
            style={{ cursor: crop ? "move" : "default" }}
            onPointerDown={(e) => {
              draggingRef.current = true;
              e.currentTarget.setPointerCapture(e.pointerId);
              setFocusFromEvent(e.clientX, e.clientY);
            }}
            onPointerMove={(e) => {
              if (draggingRef.current) {
                setFocusFromEvent(e.clientX, e.clientY);
              }
            }}
            onPointerUp={() => {
              draggingRef.current = false;
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={src}
              alt=""
              draggable={false}
              onLoad={(e) =>
                setImgAspect(
                  e.currentTarget.naturalWidth /
                    e.currentTarget.naturalHeight || null,
                )
              }
              className="block h-auto max-h-[60vh] w-auto max-w-full"
            />
            {crop && (
              // The crop box: everything outside it is dimmed by the large
              // spread box-shadow (clipped to the image by overflow-hidden),
              // so the bright rectangle is exactly what the page will show.
              <div
                className="pointer-events-none absolute rounded-sm ring-2 ring-white/90"
                style={{
                  left: `${cropLeft}%`,
                  top: `${cropTop}%`,
                  width: `${crop.w}%`,
                  height: `${crop.h}%`,
                  boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.5)",
                }}
              />
            )}
          </div>
        </div>
      )}

      <input type="hidden" name="image_focus_x" value={focusX} />
      <input type="hidden" name="image_focus_y" value={focusY} />
    </div>
  );
}
