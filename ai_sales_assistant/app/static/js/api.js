// Thin client for the existing REST API. All generation logic lives in the backend.
// Authentication uses an HttpOnly session cookie sent automatically by the browser:
// no token is ever read, stored or sent by this code.

import { t } from "./i18n.js";

const API_BASE = "/api/v1";

// Friendly messages for the error codes the API returns in `error.code`, in the interface language.
const ERROR_MESSAGES = {
  validation_error: t("js.error.validation_error", "Revisa los campos marcados."),
  invalid_json: t("js.error.invalid_json", "La petición no es válida. Recarga la página e inténtalo de nuevo."),
  ai_provider_error: t("js.error.ai_provider_error", "El proveedor de IA no ha podido generar el contenido. Inténtalo de nuevo en unos momentos."),
  ai_provider_not_configured: t("js.error.ai_provider_not_configured", "El proveedor de IA no está configurado. Revisa la configuración del servidor."),
  not_found: t("js.error.not_found", "Esta generación ya no existe. Puede que se haya eliminado."),
  not_authenticated: t("js.error.not_authenticated", "Tu sesión ha caducado. Vuelve a iniciar sesión."),
  invalid_credentials: t("js.error.invalid_credentials", "Usuario o contraseña incorrectos."),
  email_already_registered: t("js.error.email_already_registered", "Ya existe una cuenta con ese email."),
  username_already_taken: t("js.error.username_already_taken", "Ese nombre de usuario ya está en uso."),
  guest_not_allowed: t("js.error.guest_not_allowed", "Esta opción necesita una cuenta registrada."),
  guest_mode_disabled: t("js.error.guest_mode_disabled", "El acceso como invitado no está disponible."),
  guest_quota_exceeded: t("js.error.guest_quota_exceeded", "Has alcanzado el límite de generaciones del modo invitado. Crea una cuenta para seguir generando."),
  invalid_current_password: t("js.error.invalid_current_password", "La contraseña actual no es correcta."),
  invalid_or_expired_token: t("js.error.invalid_or_expired_token", "El enlace para restablecer la contraseña no es válido o ha caducado. Solicita uno nuevo."),
  csrf_failed: t("js.error.csrf_failed", "La petición se ha bloqueado por seguridad. Recarga la página e inténtalo de nuevo."),
  commercial_terms_missing: t("js.error.commercial_terms_missing", "El texto generado omitía datos comerciales obligatorios incluso tras reintentarlo, y no se ha guardado. Inténtalo de nuevo."),
  internal_error: t("js.error.internal_error", "Se ha producido un error inesperado en el servidor."),
};

export class ApiError extends Error {
  constructor(message, { status = 0, code = "network_error", details = [] } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Called when the session is missing or expired (401 not_authenticated). Pages set it to redirect to the login.
let onUnauthorized = () => {};

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      credentials: "same-origin",
      ...options,
    });
  } catch {
    throw new ApiError(t("js.error.network", "No se ha podido conectar con el servidor. Comprueba que la aplicación está en marcha."));
  }

  const body = await response.json().catch(() => null);
  if (response.ok) {
    return body;
  }

  // Common error format: {"error": {"code", "message", "details": [...]}}
  const error = body?.error ?? {};
  const code = error.code ?? "http_error";
  const message =
    ERROR_MESSAGES[code] ??
    t("js.error.http", "Error {status}: {message}", { status: response.status, message: error.message ?? response.statusText });
  if (code === "not_authenticated") onUnauthorized();
  throw new ApiError(message, { status: response.status, code, details: error.details ?? [] });
}

export function generate(data) {
  return request("/generate", { method: "POST", body: JSON.stringify(data) });
}

/** Regenerates an existing generation with AI from new input, keeping the same record. */
export function updateGeneration(id, data) {
  return request(`/generations/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(data) });
}

/** Creates a new generation, or regenerates `editingId` when given. */
export function saveGeneration(data, editingId = null) {
  return editingId ? updateGeneration(editingId, data) : generate(data);
}

export async function deleteGeneration(id) {
  // 204 No Content: there is no body to return.
  await request(`/generations/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function listGenerations({ limit = 10, offset = 0, contentType = "" } = {}) {
  const params = new URLSearchParams({ limit, offset });
  if (contentType) {
    params.set("content_type", contentType);
  }
  return request(`/generations?${params}`);
}

// --- Authentication ------------------------------------------------------------------

const post = (path, data) => request(path, { method: "POST", body: JSON.stringify(data) });

export const register = (data) => post("/auth/register", data);
export const login = (data) => post("/auth/login", data);
export const changePassword = (data) => post("/auth/change-password", data);
export const forgotPassword = (data) => post("/auth/forgot-password", data);
export const resetPassword = (data) => post("/auth/reset-password", data);
export const currentUser = () => request("/auth/me");
/** Starts a guest session: the backend sets the HttpOnly cookie, nothing is stored in the browser. */
export const startGuest = () => request("/auth/guest", { method: "POST" });

export async function logout() {
  await request("/auth/logout", { method: "POST" });
}

// --- Pricing -----------------------------------------------------------------------------

/** Discount breakdown calculated by the backend (the browser never calculates prices). */
export function pricingPreview(price, discountPercent = "") {
  const params = new URLSearchParams({ price });
  if (discountPercent) params.set("discount_percent", discountPercent);
  return request(`/pricing/discount?${params}`);
}
