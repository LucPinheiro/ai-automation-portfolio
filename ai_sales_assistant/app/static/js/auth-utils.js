// Pure helpers for the authentication pages (no DOM), tested with Node.
import { t } from "./i18n.js";

export const DEFAULT_AFTER_LOGIN = "/app";

/** Only same-site paths are accepted as a post-login destination (prevents open redirects). */
export function safeNextPath(value) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return DEFAULT_AFTER_LOGIN;
  }
  return value;
}

/** Client-side check mirroring the API rules; returns {field: message} for the problems found. */
export function passwordErrors(password, confirmation, { min = 8, max = 128, field = "password", confirmField } = {}) {
  const errors = {};
  if (password.length < min) errors[field] = t("js.password.too_short", "La contraseña debe tener al menos {min} caracteres.", { min });
  else if (password.length > max) errors[field] = t("js.password.too_long", "La contraseña no puede superar {max} caracteres.", { max });
  if (confirmField && confirmation !== password) errors[confirmField] = t("js.field.password_mismatch", "Las contraseñas no coinciden.");
  return errors;
}

/** Reads the reset token from a query string; empty string when missing. */
export function resetTokenFrom(search) {
  return new URLSearchParams(search).get("token")?.trim() ?? "";
}
