// Interface texts for the JavaScript. The server embeds the catalog of the interface language
// (keys "js.*" from app/i18n) in <script id="i18n-messages">. Every call keeps the Spanish text as
// its fallback, so the modules also work, and are tested with Node, without a page;
// tests/test_i18n.py checks that each fallback is exactly the Spanish catalog text.

function loadCatalog() {
  if (typeof document === "undefined") return {};
  try {
    return JSON.parse(document.getElementById("i18n-messages")?.textContent ?? "{}");
  } catch {
    return {};
  }
}

const catalog = loadCatalog();

/** The text for `key` in the interface language, with {name} placeholders filled from `params`. */
export function t(key, fallback, params = {}) {
  const text = catalog[key] ?? fallback;
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
}

// Number and date formats follow the interface language (<html lang>).
const LOCALES = { es: "es-ES", en: "en-GB", pt: "pt-PT", fr: "fr-FR" };
export const locale = (typeof document !== "undefined" && LOCALES[document.documentElement.lang]) || "es-ES";
