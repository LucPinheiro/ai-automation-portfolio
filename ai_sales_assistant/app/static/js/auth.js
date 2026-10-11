// Login, registration, password recovery and change-password pages.
import { changePassword, forgotPassword, login, register, resetPassword, startGuest } from "./api.js";
import { passwordErrors, resetTokenFrom, safeNextPath } from "./auth-utils.js";
import { AuthForm } from "./forms.js";
import { t } from "./i18n.js";
import { setLoading, show } from "./ui.js";

const $ = (id) => document.getElementById(id);
const field = (form, name) => form.form.elements.namedItem(name);
// The server renders the API's password limits as minlength/maxlength on new-password inputs.
const limitsInput = document.querySelector('input[type="password"][minlength]');
const min = limitsInput?.minLength ?? 8;
const max = limitsInput?.maxLength ?? 128;

function wire(formId, { validate = () => ({}), submit, busyLabel }) {
  const element = $(formId);
  if (!element) return;
  const form = new AuthForm(element);
  element.addEventListener("submit", async (event) => {
    event.preventDefault();
    form.clearMessages();
    if (form.showFieldErrors({ ...form.checkRequired(), ...validate(form) })) return;
    try {
      await form.run(() => submit(form), busyLabel);
    } catch (error) {
      form.showApiError(error);
    }
  });
}

wire("login-form", {
  busyLabel: t("js.auth.signing_in", "Entrando…"),
  submit: async (form) => {
    const { identifier, password } = form.values();
    const user = await login({ identifier, password });
    // The demo credentials open a guest session, which always starts in the generator.
    window.location.assign(user.is_guest ? "/app" : safeNextPath(form.form.dataset.next));
  },
});

// "Entrar sin iniciar sesión": the backend creates a guest user and session (HttpOnly cookie).
// The form also works on its own (POST /guest); this only adds a spinner and inline errors.
$("guest-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const guestButton = $("guest-button");
  const guestError = $("guest-error");
  show(guestError, false);
  setLoading(guestButton, true, t("js.auth.signing_in", "Entrando…"));
  try {
    await startGuest();
    window.location.assign("/app");
  } catch (error) {
    guestError.textContent = error.message;
    show(guestError, true);
    setLoading(guestButton, false);
  }
});

wire("register-form", {
  busyLabel: t("js.auth.creating_account", "Creando cuenta…"),
  validate: (form) =>
    passwordErrors(field(form, "password").value, field(form, "password_confirm").value, {
      min,
      max,
      field: "password",
      confirmField: "password_confirm",
    }),
  submit: async (form) => {
    // The API logs the new account in (session cookie), so go straight to the app.
    await register(form.values());
    window.location.assign("/app");
  },
});

wire("forgot-form", {
  busyLabel: t("js.auth.sending", "Enviando…"),
  submit: async (form) => {
    // Same answer whether or not the account exists (no user enumeration).
    await forgotPassword(form.values());
    form.showSuccess(
      t(
        "js.auth.forgot_sent",
        "Si existe una cuenta con ese email, te hemos enviado un enlace para restablecer la contraseña. Revisa tu bandeja de entrada (el enlace caduca en unos minutos).",
      ),
    );
    form.form.querySelector("[data-form-fields]").classList.add("d-none");
  },
});

// Reset page: take the token from the URL, then remove it from the address bar and history.
const resetForm = $("reset-form");
if (resetForm) {
  const token = resetTokenFrom(window.location.search);
  window.history.replaceState(null, "", window.location.pathname);
  if (!token) {
    resetForm.classList.add("d-none");
    $("reset-missing-token").classList.remove("d-none");
  }
  wire("reset-form", {
    busyLabel: t("js.auth.saving", "Guardando…"),
    validate: (form) =>
      passwordErrors(field(form, "new_password").value, field(form, "new_password_confirm").value, {
        min,
        max,
        field: "new_password",
        confirmField: "new_password_confirm",
      }),
    submit: async (form) => {
      await resetPassword({ token, ...form.values() });
      window.location.assign("/login?notice=password_reset");
    },
  });
}

wire("change-password-form", {
  busyLabel: t("js.auth.saving", "Guardando…"),
  validate: (form) =>
    passwordErrors(field(form, "new_password").value, field(form, "new_password_confirm").value, {
      min,
      max,
      field: "new_password",
      confirmField: "new_password_confirm",
    }),
  submit: async (form) => {
    await changePassword(form.values());
    form.form.reset();
    form.showSuccess(
      t("js.auth.password_changed", "Contraseña actualizada. Se han cerrado tus sesiones en otros dispositivos."),
    );
  },
});
