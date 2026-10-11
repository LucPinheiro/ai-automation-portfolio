// Shared behaviour for the authentication forms: field errors, alerts and the busy state.
import { t } from "./i18n.js";
import { setLoading, show } from "./ui.js";

// Messages for API validation errors on the auth forms (by Pydantic error type), in the interface language.
const FIELD_MESSAGES = {
  missing: t("js.field.required", "Este campo es obligatorio."),
  string_too_short: t("js.field.too_short", "Este campo es demasiado corto."),
  string_too_long: t("js.field.too_long", "Este campo es demasiado largo."),
  value_error: t("js.field.email", "El email no es válido."),
  password_mismatch: t("js.field.password_mismatch", "Las contraseñas no coinciden."),
  string_pattern_mismatch: t("js.field.username_pattern", "Usa solo letras, números, punto, guion o guion bajo."),
};

export class AuthForm {
  constructor(form) {
    this.form = form;
    this.button = form.querySelector('button[type="submit"]');
    this.error = form.querySelector("[data-form-error]");
    this.success = form.querySelector("[data-form-success]");
    form.addEventListener("input", (event) => event.target.classList.remove("is-invalid"));
  }

  values() {
    return Object.fromEntries(new FormData(this.form));
  }

  clearMessages() {
    this.form.querySelectorAll(".is-invalid").forEach((field) => field.classList.remove("is-invalid"));
    this.showError("");
    this.showSuccess("");
  }

  showError(message) {
    this.error.textContent = message;
    show(this.error, Boolean(message));
  }

  showSuccess(message) {
    this.success.textContent = message;
    show(this.success, Boolean(message));
  }

  /** Marks fields as invalid; returns true when at least one error was shown. */
  showFieldErrors(errors) {
    const entries = Object.entries(errors);
    for (const [name, message] of entries) {
      const field = this.form.elements.namedItem(name);
      const feedback = this.form.querySelector(`[data-error-for="${name}"]`);
      if (!field || !feedback) continue;
      field.classList.add("is-invalid");
      feedback.textContent = message;
    }
    if (entries.length) this.form.elements.namedItem(entries[0][0])?.focus();
    return entries.length > 0;
  }

  /** Required fields and email format, checked before calling the API. */
  checkRequired() {
    const errors = {};
    for (const field of this.form.elements) {
      if (!field.name || field.type === "submit") continue;
      if (!field.value) {
        if (field.required) errors[field.name] = FIELD_MESSAGES.missing;
      } else if (field.type === "email" && !field.checkValidity()) errors[field.name] = FIELD_MESSAGES.value_error;
    }
    return errors;
  }

  /** Shows an ApiError: per-field details next to the inputs, the rest in the alert. */
  showApiError(error) {
    const fieldErrors = {};
    for (const detail of error.details ?? []) {
      if (detail.field && this.form.elements.namedItem(detail.field)) {
        fieldErrors[detail.field] = FIELD_MESSAGES[detail.type] ?? detail.message;
      }
    }
    this.showFieldErrors(fieldErrors);
    this.showError(error.message);
  }

  async run(action, busyLabel) {
    setLoading(this.button, true, busyLabel);
    try {
      return await action();
    } finally {
      setLoading(this.button, false);
    }
  }
}
