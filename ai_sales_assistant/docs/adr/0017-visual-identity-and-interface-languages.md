# 0017. Visual identity, access screens and interface languages

- Status: Accepted; the interface languages part is superseded by [SDD 12](../specs/12-sdd.md#53-idiomas-de-la-interfaz)
- Date: 2026-10-08

> **Partially superseded (2026-10-09).** The visual identity and the access screens below remain valid. The interface
> languages design (Spanish only, catalog only on the redesigned screens) was replaced by the multilingual design in
> [SDD 12 § 5.3](../specs/12-sdd.md#53-idiomas-de-la-interfaz): Spanish, English, Portuguese and French, the
> `/language/<code>` switch, every screen and the JavaScript texts translated, and guarantees enforced by `tests/test_i18n.py`.

## Context

The access screens used generic Bootstrap cards and a placeholder logo. The product needs its own identity (logo, colours, slogan "Tu asistente comercial inteligente"), a cleaner access page inspired by turquoise, two-column banking-style logins (composition only: no third-party brand, logo or text), public information pages, and an interface ready for future languages. Spanish is the main language. Authentication, guest mode and demo access must not change.

## Decision

**Identity.** Original logo: a conversation bubble (communication, sales) with an AI spark cut out of it, drawn as a single SVG path with `fill-rule="evenodd"` and `currentColor`, so the same mark works white on turquoise and turquoise on white. Files in `app/static/img/`: `logo-mark.svg` (favicon/app icon), `logo-mark-teal.svg`, `logo-mark-white.svg`, `logo-full-teal.svg`, `logo-full-white.svg`. In templates the mark is inline (`_brand.html`) and the wordmark is real text. No external resources or fonts (system font stack).

**Colours** (`brand.css`), chosen by measured WCAG 2.1 contrast and checked by `tests/test_branding.py`: background turquoise `#00827F` (white text 4.67:1), buttons/links `#0B6F6B` (6.0:1 with white), ink `#12303A`, muted `#4E6670`; the brighter `#19B3AC` is used only for decoration and focus rings, never behind text. A brighter turquoise was rejected because white body text on it fails AA (3.45:1).

**Access screens.** `auth_base.html` is a two-column layout on turquoise: white access card on the left, product presentation on the right, white footer; below 992 px it stacks (card first). Login, register and password recovery share it. Forms keep their ids and real `POST /login` / `POST /guest` actions, so they work without JavaScript. The public demo values (`demo` / `demo123`) stay pre-filled with the hint "Demo: demo / demo123"; they still only open a guest session (ADR 0014). "Probar sin registrarse" is a secondary action with its limits stated.

**Interface languages** (`app/i18n/`) — *superseded by [SDD 12 § 5.3](../specs/12-sdd.md#53-idiomas-de-la-interfaz); kept for history*: `SUPPORTED_LANGUAGES = {"es": "Español"}`, a Spanish catalog (`es.py`) and `translator(language)` exposed to templates as `t("key")`; `resolve_language` reads an optional `ui_lang` cookie and falls back to Spanish. The selector ("ES ▾") and `<html lang>` are built from that list. Only the new and redesigned screens use the catalog for now; the rest of the app is migrated when languages are added. This is the interface language, independent of the language of the generated content (a form field).

**Public pages**: `/contacto`, `/legal`, `/privacidad` (no session, not in OpenAPI) and a shared footer on every screen. No legal or contact data is invented: sections say "Pendiente de completar." and the support email comes from the optional `SUPPORT_EMAIL` setting.

## Consequences

- Adding a language = one catalog module and one entry in `SUPPORTED_LANGUAGES`; a test fails if a template uses a key missing from the catalog.
- The access background is a deeper turquoise than the reference so that all text meets AA.
- The app interior keeps its Bootstrap styling for now (only logo, slogan and footer changed).
