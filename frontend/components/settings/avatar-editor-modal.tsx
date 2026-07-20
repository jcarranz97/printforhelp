"use client";

import { Button, Modal } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { FiMinus, FiPlus } from "react-icons/fi";

import { type AvatarCrop, UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";

/** How far in the user may zoom: 4x the largest square that fits. */
const MAX_ZOOM = 4;
/** Multiplier per wheel notch / button press. */
const ZOOM_STEP = 1.12;

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));
const round2 = (value: number) => Math.round(value * 100) / 100;

/**
 * The crop for a given zoom, centred on (`cx`, `cy`) in image percent.
 *
 * The avatar is square, so at zoom 1 the crop is the largest square that fits
 * the picture: full width for a portrait, full height for a landscape. Zooming
 * shrinks that square by `zoom`, keeping it square in *pixels* — which is why
 * the width and height percentages differ on a non-square image.
 */
function cropFor(
  aspect: number,
  zoom: number,
  cx: number,
  cy: number,
): AvatarCrop {
  const baseW = aspect <= 1 ? 100 : (1 / aspect) * 100;
  const baseH = aspect <= 1 ? aspect * 100 : 100;
  const w = baseW / zoom;
  const h = baseH / zoom;
  return {
    x: round2(clamp(cx - w / 2, 0, 100 - w)),
    y: round2(clamp(cy - h / 2, 0, 100 - h)),
    w: round2(w),
    h: round2(h),
  };
}

/** Recover the zoom level from a crop (used when re-opening the editor). */
function zoomFromCrop(aspect: number, crop: AvatarCrop): number {
  const baseW = aspect <= 1 ? 100 : (1 / aspect) * 100;
  return clamp(baseW / crop.w, 1, MAX_ZOOM);
}

type AvatarEditorModalProps = {
  isOpen: boolean;
  username: string;
  fullName: string | null;
  imageUrl: string;
  /** The crop to open with (the saved one, or a fresh upload's default). */
  initialCrop: AvatarCrop;
  onApply: (crop: AvatarCrop) => void;
  onCancel: () => void;
};

/**
 * Modal for choosing which part of a picture becomes the avatar. Opened right
 * after a new photo is picked (and from "Adjust" for an existing one), so the
 * crop controls only appear when they are actually needed rather than sitting
 * on the settings page permanently.
 */
export function AvatarEditorModal({
  isOpen,
  username,
  fullName,
  imageUrl,
  initialCrop,
  onApply,
  onCancel,
}: AvatarEditorModalProps) {
  const { dict } = useI18n();
  const t = dict.settingsProfile;

  return (
    <Modal.Backdrop
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open) {
          onCancel();
        }
      }}
    >
      <Modal.Container>
        <Modal.Dialog className="sm:max-w-[560px]">
          <Modal.Header>
            <Modal.Heading>{t.pictureModalTitle}</Modal.Heading>
          </Modal.Header>
          {/* Mounted only while open, so the editor always starts from the
              crop it was handed and its wheel listener binds on mount. */}
          {isOpen ? (
            <CropEditor
              username={username}
              fullName={fullName}
              imageUrl={imageUrl}
              initialCrop={initialCrop}
              onApply={onApply}
              onCancel={onCancel}
            />
          ) : null}
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  );
}

function CropEditor({
  username,
  fullName,
  imageUrl,
  initialCrop,
  onApply,
  onCancel,
}: Omit<AvatarEditorModalProps, "isOpen">) {
  const { dict } = useI18n();
  const t = dict.settingsProfile;

  const pickerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);
  const [aspect, setAspect] = useState<number | null>(null);
  const [crop, setCrop] = useState<AvatarCrop>(initialCrop);

  // Latest values for the wheel listener, which is bound once (see below).
  const stateRef = useRef({ crop, aspect });
  stateRef.current = { crop, aspect };

  function measure(el: HTMLImageElement | null) {
    if (el?.complete && el.naturalWidth > 0 && aspect === null) {
      const ratio = el.naturalWidth / el.naturalHeight || 1;
      setAspect(ratio);
      // A picture with no crop yet starts as the largest centred square.
      if (initialCrop.w >= 99.99 && initialCrop.h >= 99.99) {
        setCrop(cropFor(ratio, 1, 50, 50));
      }
    }
  }

  /** Zoom by `factor`, keeping the circle's centre fixed. */
  function zoomBy(factor: number) {
    const { crop: current, aspect: ratio } = stateRef.current;
    if (!ratio) {
      return;
    }
    const zoom = zoomFromCrop(ratio, current);
    const next = clamp(zoom * factor, 1, MAX_ZOOM);
    setCrop(
      cropFor(
        ratio,
        next,
        current.x + current.w / 2,
        current.y + current.h / 2,
      ),
    );
  }

  /**
   * Wheel-to-zoom. Bound natively with `passive: false` because React's
   * synthetic wheel handler cannot reliably `preventDefault()`, and without
   * that the page would scroll behind the modal while zooming.
   */
  useEffect(() => {
    const el = pickerRef.current;
    if (!el) {
      return;
    }
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      zoomBy(event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
    // Bound once: the handler reads the latest state through `stateRef`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Treat the pointer as the circle's centre, clamped so it stays in the image.
  function moveTo(clientX: number, clientY: number) {
    const el = pickerRef.current;
    if (!el || !aspect) {
      return;
    }
    const rect = el.getBoundingClientRect();
    setCrop(
      cropFor(
        aspect,
        zoomFromCrop(aspect, crop),
        ((clientX - rect.left) / rect.width) * 100,
        ((clientY - rect.top) / rect.height) * 100,
      ),
    );
  }

  return (
    <>
      <Modal.Body className="flex flex-col items-center gap-4">
        <div
          ref={pickerRef}
          className="relative inline-block max-w-full touch-none select-none overflow-hidden rounded-lg border border-border"
          style={{ cursor: "move" }}
          onPointerDown={(e) => {
            draggingRef.current = true;
            e.currentTarget.setPointerCapture(e.pointerId);
            moveTo(e.clientX, e.clientY);
          }}
          onPointerMove={(e) => {
            if (draggingRef.current) {
              moveTo(e.clientX, e.clientY);
            }
          }}
          onPointerUp={() => {
            draggingRef.current = false;
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={measure}
            src={imageUrl}
            alt=""
            draggable={false}
            onLoad={(e) => measure(e.currentTarget)}
            className="block h-auto max-h-[46vh] w-auto max-w-full"
          />
          {aspect ? (
            // The circle: everything outside is dimmed by the large spread
            // box-shadow (clipped to the image by overflow-hidden), so the
            // bright disc is exactly what the avatar will show.
            <div
              className="pointer-events-none absolute rounded-full ring-2 ring-white/90"
              style={{
                left: `${crop.x}%`,
                top: `${crop.y}%`,
                width: `${crop.w}%`,
                height: `${crop.h}%`,
                boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.5)",
              }}
            />
          ) : null}
        </div>

        <div className="flex items-center gap-4">
          {/* The wheel is the primary control; these keep zoom reachable on
              touch devices and by keyboard, which a wheel cannot serve. */}
          <Button
            isIconOnly
            size="sm"
            variant="tertiary"
            aria-label={t.pictureZoomOut}
            onPress={() => zoomBy(1 / ZOOM_STEP)}
          >
            <FiMinus />
          </Button>
          <UserAvatar
            username={username}
            fullName={fullName}
            avatarUrl={imageUrl}
            crop={crop}
            className="size-16"
            fallbackClassName="text-lg"
          />
          <Button
            isIconOnly
            size="sm"
            variant="tertiary"
            aria-label={t.pictureZoomIn}
            onPress={() => zoomBy(ZOOM_STEP)}
          >
            <FiPlus />
          </Button>
        </div>
        <p className="text-center text-xs text-muted">{t.pictureAdjustHint}</p>
      </Modal.Body>
      <Modal.Footer className="flex-col-reverse sm:flex-row sm:justify-end">
        <Button variant="tertiary" onPress={onCancel}>
          {t.pictureCancel}
        </Button>
        <Button onPress={() => onApply(crop)}>{t.pictureApply}</Button>
      </Modal.Footer>
    </>
  );
}
