// Small DOM helpers shared by the page. Content is always set with textContent, never innerHTML.
import { locale } from "./i18n.js";

const dateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" });

export function show(element, visible = true) {
  element.classList.toggle("d-none", !visible);
}

export function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date);
}

export function createElement(tag, { className = "", text = "" } = {}) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

export function badge(text, variant = "secondary") {
  return createElement("span", { className: `badge text-bg-${variant}`, text });
}

export function setLoading(button, loading, loadingLabel) {
  const label = button.querySelector(".button-label");
  button.dataset.label ??= label.textContent;
  button.disabled = loading;
  button.setAttribute("aria-busy", String(loading));
  show(button.querySelector(".spinner-border"), loading);
  label.textContent = loading ? loadingLabel : button.dataset.label;
}

// Copies clean text; when `html` is given and supported, also a formatted version for email clients.
export async function copyText(text, html = "") {
  if (navigator.clipboard && window.isSecureContext) {
    if (html && window.ClipboardItem) {
      try {
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/plain": new Blob([text], { type: "text/plain" }),
            "text/html": new Blob([html], { type: "text/html" }),
          }),
        ]);
        return;
      } catch {
        // Some browsers reject text/html; fall back to plain text below.
      }
    }
    await navigator.clipboard.writeText(text);
    return;
  }
  // Fallback for non-secure origins (e.g. the app opened through a LAN IP over http).
  const textarea = createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("copy failed");
}

export function flashButton(button, text, ms = 1500) {
  const original = button.textContent;
  button.textContent = text;
  setTimeout(() => {
    button.textContent = original;
  }, ms);
}
