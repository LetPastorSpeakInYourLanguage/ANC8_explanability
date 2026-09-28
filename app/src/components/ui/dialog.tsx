"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface DialogProps extends Omit<React.HTMLAttributes<HTMLDialogElement>, "onClose"> {
  open: boolean;
  /** Omit to make the dialog non-dismissible — no Esc, no backdrop click. Used for a
   *  blocking progress panel that must not be closable mid-operation (see RegistryClient's
   *  pull-progress panel, ported from its old hand-rolled Modal). */
  onClose?: () => void;
}

/**
 * A native `<dialog>`-backed modal — free focus-trapping and Esc-to-close from the
 * platform, in place of hand-rolling both (RegistryClient.tsx's old `Modal` did exactly
 * that with a manual keydown listener and a `role="dialog"` div).
 *
 * Kept deliberately tier-agnostic: title/body/footer are plain layout slots, not an
 * info/confirm/commit variant prop. The three-tier vocabulary (a commit dialog with
 * server-computed counts and a risk checkbox) is the launch-preview work's to add on top
 * of this, not this component's to anticipate.
 */
export function Dialog({ open, onClose, className, children, ...rest }: DialogProps) {
  const ref = React.useRef<HTMLDialogElement>(null);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    else if (!open && el.open) el.close();
  }, [open]);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // Esc fires `cancel` before the dialog closes itself — block the default close when
    // there's nowhere for that to go (no onClose), otherwise route it through the same
    // handler the backdrop click uses.
    function onCancel(e: Event) {
      if (!onClose) {
        e.preventDefault();
        return;
      }
      onClose();
    }
    el.addEventListener("cancel", onCancel);
    return () => el.removeEventListener("cancel", onCancel);
  }, [onClose]);

  function onBackdropClick(e: React.MouseEvent<HTMLDialogElement>) {
    // A native <dialog> box is sized to its content, so a click that lands on the dialog
    // element itself (not a child) is a click on the backdrop — same target-equality check
    // the old hand-rolled Modal used.
    if (onClose && e.target === e.currentTarget) onClose();
  }

  if (!open) return null;

  return (
    <dialog
      ref={ref}
      onClick={onBackdropClick}
      className={cn(
        "m-auto w-full max-w-420 border-0 bg-transparent p-0 text-text",
        "[&::backdrop]:bg-[color-mix(in_srgb,var(--bg)_78%,transparent)]",
        className,
      )}
      {...rest}
    >
      <div className="border border-border2 bg-panel flex flex-col gap-10 p-16">{children}</div>
    </dialog>
  );
}

export function DialogTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-11.5 text-text", className)} {...props} />;
}

export function DialogBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-10 text-10.5 leading-relaxed text-dim", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex gap-8 justify-end pt-2", className)} {...props} />;
}
