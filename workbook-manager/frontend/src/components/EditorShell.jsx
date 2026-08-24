import React, { useId, useLayoutEffect, useRef } from "react";
import { X } from "lucide-react";

const FOCUSABLE = [
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "a[href]",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export default function EditorShell({
  title,
  subtitle,
  target,
  dirty,
  busy,
  onRequestClose,
  children,
  footer,
}) {
  const headingId = useId();
  const shellRef = useRef(null);
  const headingRef = useRef(null);
  const openerRef = useRef(
    typeof document === "undefined" ? null : document.activeElement,
  );

  const requestClose = () => {
    if (busy) return;
    if (dirty && !window.confirm("Discard unsaved editor changes?")) return;
    onRequestClose();
  };

  useLayoutEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    headingRef.current?.focus();
    const opener = openerRef.current;
    return () => {
      document.body.style.overflow = previousOverflow;
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      requestClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...shellRef.current.querySelectorAll(FOCUSABLE)];
    if (!focusable.length) {
      event.preventDefault();
      headingRef.current?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      className="editor-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) requestClose();
      }}
    >
      <section
        ref={shellRef}
        className="editor-shell"
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        onKeyDown={handleKeyDown}
      >
        <header className="editor-header">
          <div>
            <div className="eyebrow">Draft editor · {target}</div>
            <h2 id={headingId} ref={headingRef} tabIndex={-1}>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button
            type="button"
            className="btn small"
            onClick={requestClose}
            disabled={busy}
            aria-label="Close editor"
          >
            <X size={16} /> Close
          </button>
        </header>
        <div className="editor-body">{children}</div>
        <footer className="editor-footer">
          {typeof footer === "function" ? footer(requestClose) : footer}
        </footer>
      </section>
    </div>
  );
}
