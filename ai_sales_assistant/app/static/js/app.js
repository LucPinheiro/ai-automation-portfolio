import { deleteGeneration, listGenerations, pricingPreview, saveGeneration } from "./api.js";
import { FORM_FIELDS, describeGeneration, formValuesFrom, normalizeDecimal, shareLinks, toApiPayload } from "./generation-form.js";
import { createIcon } from "./icons.js";
import { findPlaceholders, parseMarkdown, renderMarkdown, toPlainText } from "./markdown.js";
import { locale, t } from "./i18n.js";
import { badge, copyText, createElement, flashButton, formatDate, setLoading, show } from "./ui.js";

const HISTORY_PAGE_SIZE = 10;

const labels = JSON.parse(document.getElementById("ui-labels").textContent);
const $ = (id) => document.getElementById(id);

// --- Generated content ---------------------------------------------------------

// What each Copy button copies, keyed by the id of the element it targets.
const copySources = new Map();

function showGeneratedContent(container, placeholdersAlert, markdown) {
  const blocks = parseMarkdown(markdown);
  renderMarkdown(container, blocks);

  // The formatted copy has no highlighting, so it pastes cleanly into email clients.
  const clean = document.createElement("div");
  renderMarkdown(clean, blocks, { highlightPlaceholders: false });
  copySources.set(container.id, { text: toPlainText(blocks), html: clean.innerHTML });

  const placeholders = findPlaceholders(blocks);
  placeholdersAlert.textContent = placeholders.length
    ? t("js.gen.placeholders", "El modelo ha dejado datos sin completar: {list}. Revísalos antes de enviar.", {
        list: placeholders.join(", "),
      })
    : "";
  show(placeholdersAlert, placeholders.length > 0);
}

// --- Generation form -------------------------------------------------------

const form = $("generate-form");
const generateButton = $("generate-button");
const result = {
  empty: $("result-empty"),
  loading: $("result-loading"),
  error: $("result-error"),
  panel: $("result"),
  meta: $("result-meta"),
  content: $("result-content"),
  placeholders: $("result-placeholders"),
  commercialMissing: $("result-commercial-missing"),
  copy: $("copy-result"),
  shareEmail: $("share-email"),
  shareWhatsApp: $("share-whatsapp"),
};

/** Enables a share link with its URL, or disables it (no href, not focusable) when there is nothing to share. */
function setShareLink(link, href) {
  if (href) link.href = href;
  else link.removeAttribute("href");
  link.classList.toggle("disabled", !href);
  link.setAttribute("aria-disabled", String(!href));
  link.tabIndex = href ? 0 : -1;
}

function updateShareLinks(generation) {
  const text = copySources.get(result.content.id)?.text ?? "";
  const links = generation && text ? shareLinks(text, generation.customer_email ?? "") : {};
  setShareLink(result.shareEmail, links.email);
  setShareLink(result.shareWhatsApp, links.whatsapp);
}

function clearFieldErrors() {
  form.querySelectorAll(".is-invalid").forEach((field) => field.classList.remove("is-invalid"));
}

const FIELD_ERROR_MESSAGES = {
  value_error: t("js.field.email", "El email no es válido."),
  discount_requires_price: t("js.gen.field.discount_requires_price", "Indica un precio para aplicar el descuento."),
  decimal_parsing: t("js.gen.field.decimal_parsing", "Introduce un número (por ejemplo 179 o 49,99)."),
  decimal_max_places: t("js.gen.field.decimal_max_places", "Usa como máximo 2 decimales."),
  decimal_max_digits: t("js.gen.field.decimal_max_digits", "El número es demasiado grande."),
  greater_than: t("js.gen.field.greater_than", "Debe ser mayor que 0."),
  greater_than_equal: t("js.gen.field.greater_than_equal", "No puede ser negativo."),
  less_than_equal: t("js.gen.field.less_than_equal", "El valor máximo es 100."),
  finite_number: t("js.gen.field.finite_number", "Introduce un número válido."),
};

function showFieldError(name, message) {
  const field = form.elements.namedItem(name);
  const feedback = form.querySelector(`[data-error-for="${name}"]`);
  if (!field || !feedback) return false;
  field.classList.add("is-invalid");
  feedback.textContent = message;
  return true;
}

// Browser-side check with the same rules as the API (required + maxlength), in the interface language.
function validateForm() {
  clearFieldErrors();
  let firstInvalid = null;
  for (const field of form.elements) {
    if (!field.name) continue;
    const value = field.value.trim();
    let message = "";
    if (!value && field.required) message = t("js.field.required", "Este campo es obligatorio.");
    else if (field.maxLength > 0 && value.length > field.maxLength) {
      message = t("js.gen.max_chars", "Máximo {max} caracteres.", { max: field.maxLength });
    }
    if (message) {
      showFieldError(field.name, message);
      firstInvalid ??= field;
    }
  }
  firstInvalid?.focus();
  return firstInvalid === null;
}

function setResultState(state) {
  show(result.empty, state === "empty");
  show(result.loading, state === "loading");
  show(result.panel, state === "result");
  result.copy.disabled = state !== "result";
  if (state !== "result") updateShareLinks(null);
}

function showResultError(message) {
  result.error.textContent = message;
  show(result.error, Boolean(message));
}

// Mandatory commercial terms the AI left out (checked by the backend after its single retry).
// The text is never edited automatically: the user sees what is missing and can regenerate.
function showMissingCommercialTerms(container, generation, { onRegenerate } = {}) {
  const missing = generation.missing_commercial_terms ?? [];
  if (!missing.length) {
    container.replaceChildren();
    show(container, false);
    return;
  }
  const list = createElement("ul", { className: "mb-2 ps-3" });
  list.append(...missing.map((term) => createElement("li", { text: term })));
  container.replaceChildren(
    createElement("strong", { text: t("js.gen.missing_terms", "El texto generado omite estos datos comerciales obligatorios:") }),
    list,
    createElement("p", { className: "mb-2", text: t("js.gen.missing_terms_hint", "Revísalo antes de enviarlo o vuelve a generarlo.") }),
  );
  if (onRegenerate) {
    const button = createElement("button", { className: "btn btn-sm btn-danger", text: t("js.gen.regenerate", "Regenerar") });
    button.type = "button";
    button.id = "regenerate-missing";
    button.addEventListener("click", () => onRegenerate(button));
    container.append(button);
  }
  show(container, true);
}

async function regenerate(generation, button) {
  button.disabled = true;
  button.textContent = t("js.gen.regenerating", "Regenerando…");
  setResultState("loading");
  try {
    renderResult(await saveGeneration(toApiPayload(formValuesFrom(generation)), generation.id));
    loadHistory();
  } catch (error) {
    showResultError(error.message);
    setResultState("result");
  }
}

function renderResult(generation) {
  result.meta.replaceChildren(
    badge(labels.content_types[generation.content_type] ?? generation.content_type, "primary"),
    badge(labels.languages[generation.language] ?? generation.language, "light border"),
    badge(labels.tones[generation.tone] ?? generation.tone, "light border"),
    createElement("span", {
      className: "text-body-secondary ms-auto",
      text: `${generation.ai_provider} · ${generation.ai_model}`,
    }),
  );
  showGeneratedContent(result.content, result.placeholders, generation.generated_content);
  showMissingCommercialTerms(result.commercialMissing, generation, {
    onRegenerate: (button) => regenerate(generation, button),
  });
  setResultState("result");
  updateShareLinks(generation);
}

// --- Pricing preview (calculated by the backend) -----------------------------------------

const euro = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" });
const percentNumber = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
// Display formatting only: the values are the backend's Decimal strings ("152.15").
const formatEuro = (value) => euro.format(Number(value));
// "15 %" in Spanish and French, "15%" in English and Portuguese (as in the generated texts).
const formatPercent = (value) =>
  `${percentNumber.format(Number(value))}${locale === "es-ES" || locale === "fr-FR" ? " " : ""}%`;

function pricingRows(pricing) {
  const rows = [[t("js.gen.price", "Precio"), formatEuro(pricing.original_price)]];
  if (pricing.discount_percent !== null) {
    rows.push(
      [t("js.gen.discount", "Descuento"), formatPercent(pricing.discount_percent)],
      [t("js.gen.saving", "Ahorras"), formatEuro(pricing.discount_amount)],
      [t("js.gen.final_price", "Precio final"), formatEuro(pricing.final_price)],
    );
  }
  return rows;
}

const pricingPreviewBox = $("pricing-preview");
const priceInput = form.elements.namedItem("price");
const discountInput = form.elements.namedItem("discount_percent");
let pricingTimer = null;
let pricingRequest = 0;

function renderPricingPreview(pricing) {
  const list = createElement("dl", { className: "pricing-breakdown mb-0" });
  for (const [term, value] of pricingRows(pricing)) {
    list.append(createElement("dt", { text: term }), createElement("dd", { text: value }));
  }
  pricingPreviewBox.replaceChildren(list);
}

async function updatePricingPreview() {
  const price = normalizeDecimal(priceInput.value);
  const discount = normalizeDecimal(discountInput.value);
  const request = ++pricingRequest;
  // The breakdown is shown when both values exist.
  if (!price || !discount) {
    show(pricingPreviewBox, false);
    return;
  }
  try {
    const pricing = await pricingPreview(price, discount);
    if (request !== pricingRequest) return; // a newer input already replaced this one
    renderPricingPreview(pricing);
  } catch {
    if (request !== pricingRequest) return;
    pricingPreviewBox.replaceChildren(
      createElement("p", {
        className: "mb-0 text-danger",
        text: t(
          "js.gen.pricing_invalid",
          "Revisa los valores: precio mayor que 0 con hasta 2 decimales y descuento entre 0 y 100.",
        ),
      }),
    );
  }
  show(pricingPreviewBox, true);
}

function schedulePricingPreview() {
  clearTimeout(pricingTimer);
  pricingTimer = setTimeout(updatePricingPreview, 300);
}

priceInput.addEventListener("input", schedulePricingPreview);
discountInput.addEventListener("input", schedulePricingPreview);

// --- Edit mode -------------------------------------------------------------------

const edit = {
  card: $("form-card"),
  title: $("form-title"),
  banner: $("edit-banner"),
  bannerLabel: $("edit-banner-label"),
  cancel: $("cancel-edit"),
  id: null,
};

const needs = form.elements.namedItem("customer_needs");
const needsCount = $("customer_needs-count");
const updateNeedsCount = () => {
  needsCount.textContent = needs.value.length;
};

function setSubmitLabel(text) {
  // setLoading restores dataset.label once loading ends, so both must change together.
  generateButton.dataset.label = text;
  generateButton.querySelector(".button-label").textContent = text;
}

function startEditing(generation) {
  edit.id = generation.id;
  const values = formValuesFrom(generation);
  for (const field of FORM_FIELDS) form.elements.namedItem(field).value = values[field];
  updateNeedsCount();
  updatePricingPreview();
  clearFieldErrors();
  showResultError("");

  edit.title.textContent = t("js.gen.edit_title", "Editar generación");
  edit.bannerLabel.textContent = describeGeneration(generation, labels.content_types);
  show(edit.banner, true);
  edit.card.classList.add("is-editing");
  setSubmitLabel(t("js.gen.update_submit", "Actualizar con IA"));
  renderHistory();

  edit.card.scrollIntoView({ behavior: "smooth", block: "start" });
  form.elements.namedItem("customer").focus({ preventScroll: true });
}

function stopEditing() {
  edit.id = null;
  form.reset();
  updateNeedsCount();
  updatePricingPreview();
  clearFieldErrors();

  edit.title.textContent = t("js.gen.new_title", "Nueva generación");
  show(edit.banner, false);
  edit.card.classList.remove("is-editing");
  setSubmitLabel(t("js.gen.submit", "Generar con IA"));
  renderHistory();
}

edit.cancel.addEventListener("click", stopEditing);

// --- Submit (create or regenerate) -----------------------------------------------

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showResultError("");
  if (!validateForm()) return;

  const data = toApiPayload(Object.fromEntries(new FormData(form)));
  const editingId = edit.id;
  setLoading(generateButton, true, t("js.gen.generating", "Generando…"));
  setResultState("loading");
  try {
    renderResult(await saveGeneration(data, editingId));
    if (editingId) stopEditing();
    loadHistory();
  } catch (error) {
    // Field errors from a 422 are shown next to each field; anything else goes in the alert.
    const unmatched = (error.details ?? []).filter(
      (detail) => !showFieldError(detail.field, FIELD_ERROR_MESSAGES[detail.type] ?? detail.message),
    );
    const extra = unmatched.map((detail) => detail.message).join(" ");
    showResultError(extra ? `${error.message} ${extra}` : error.message);
    setResultState(copySources.has(result.content.id) ? "result" : "empty");
    // The record was deleted meanwhile: leave edit mode so the user can create a new one.
    if (editingId && error.code === "not_found") {
      stopEditing();
      loadHistory();
    }
  } finally {
    setLoading(generateButton, false);
  }
});

form.addEventListener("input", (event) => event.target.classList.remove("is-invalid"));
needs.addEventListener("input", updateNeedsCount);

// --- Copy buttons ------------------------------------------------------------

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy-target]");
  if (!button) return;
  try {
    const source = copySources.get(button.dataset.copyTarget);
    if (!source) return;
    await copyText(source.text, source.html);
    flashButton(button, t("js.gen.copied", "¡Copiado!"));
  } catch {
    flashButton(button, t("js.gen.copy_failed", "No se pudo copiar"));
  }
});

// --- History -----------------------------------------------------------------

const historyView = {
  table: $("history-table"),
  body: $("history-body"),
  total: $("history-total"),
  empty: $("history-empty"),
  error: $("history-error"),
  more: $("history-more"),
  filter: $("history-filter"),
  refresh: $("history-refresh"),
  items: [],
  totalCount: 0,
};

const detail = {
  modal: new bootstrap.Modal($("detail-modal")),
  title: $("detail-title"),
  meta: $("detail-meta"),
  content: $("detail-content"),
  placeholders: $("detail-placeholders"),
};

function openDetail(generation) {
  detail.title.textContent = labels.content_types[generation.content_type] ?? generation.content_type;
  const rows = [
    [t("js.gen.customer", "Cliente"), generation.customer],
    [t("js.gen.company", "Empresa del cliente"), generation.company],
    [t("js.gen.industry", "Sector"), generation.industry],
    [t("js.gen.product", "Producto o servicio"), generation.product_or_service],
    [t("js.gen.salesperson", "Comercial"), generation.salesperson || "—"],
    [t("js.gen.salesperson_company", "Empresa del comercial"), generation.salesperson_company || "—"],
    ...(generation.pricing ? pricingRows(generation.pricing) : [[t("js.gen.price", "Precio"), "—"]]),
    [t("js.gen.needs", "Necesidades"), generation.customer_needs],
    [
      t("js.gen.language_tone", "Idioma / Tono"),
      `${labels.languages[generation.language] ?? generation.language} · ${labels.tones[generation.tone] ?? generation.tone}`,
    ],
    [t("js.gen.model", "Modelo"), `${generation.ai_provider} · ${generation.ai_model}`],
    [t("js.gen.date", "Fecha"), formatDate(generation.created_at)],
  ];
  detail.meta.replaceChildren(
    ...rows.flatMap(([term, value]) => [
      createElement("dt", { className: "col-sm-4 text-body-secondary fw-normal", text: term }),
      createElement("dd", { className: "col-sm-8", text: value }),
    ]),
  );
  showGeneratedContent(detail.content, detail.placeholders, generation.generated_content);
  showMissingCommercialTerms($("detail-commercial-missing"), generation);
  detail.modal.show();
}

// --- Delete ----------------------------------------------------------------------

const removal = {
  modal: new bootstrap.Modal($("delete-modal")),
  summary: $("delete-summary"),
  error: $("delete-error"),
  confirm: $("delete-confirm"),
  generation: null,
};

function confirmDelete(generation) {
  removal.generation = generation;
  removal.summary.textContent = describeGeneration(generation, labels.content_types);
  show(removal.error, false);
  removal.modal.show();
}

removal.confirm.addEventListener("click", async () => {
  const { generation } = removal;
  if (!generation) return;
  show(removal.error, false);
  setLoading(removal.confirm, true, t("js.gen.deleting", "Eliminando…"));
  try {
    await deleteGeneration(generation.id);
    removal.modal.hide();
    if (edit.id === generation.id) stopEditing();
    loadHistory();
  } catch (error) {
    if (error.code === "not_found") {
      // Already gone: the goal is met, just refresh.
      removal.modal.hide();
      if (edit.id === generation.id) stopEditing();
      loadHistory();
    } else {
      removal.error.textContent = t("js.gen.delete_failed", "No se pudo eliminar. {message}", { message: error.message });
      show(removal.error, true);
    }
  } finally {
    setLoading(removal.confirm, false);
  }
});

// --- History rows --------------------------------------------------------------------

// Tooltips of the current history rows, disposed before the rows are replaced.
const rowTooltips = new Set();

function actionButton({ icon, tooltip, label, variant, onClick }) {
  const button = createElement("button", { className: `btn btn-outline-${variant} btn-icon` });
  button.type = "button";
  button.title = tooltip;
  button.setAttribute("aria-label", label);
  button.append(createIcon(document, icon));

  // Hover only: on focus, the modals return focus to the button and would leave the tooltip stuck open.
  const tooltipInstance = new bootstrap.Tooltip(button, { trigger: "hover" });
  rowTooltips.add(tooltipInstance);
  button.addEventListener("click", () => {
    tooltipInstance.hide();
    onClick();
  });
  return button;
}

function disposeRowTooltips() {
  rowTooltips.forEach((tooltipInstance) => tooltipInstance.dispose());
  rowTooltips.clear();
}

function historyRow(generation) {
  const row = createElement("tr");
  if (generation.id === edit.id) row.classList.add("table-info");

  const actions = createElement("div", { className: "history-actions" });
  actions.append(
    actionButton({
      icon: "eye",
      tooltip: t("js.gen.view", "Ver"),
      label: t("js.gen.view_label", "Ver generación"),
      variant: "primary",
      onClick: () => openDetail(generation),
    }),
    actionButton({
      icon: "pencil",
      tooltip: t("js.gen.edit", "Editar"),
      label: t("js.gen.edit_title", "Editar generación"),
      variant: "secondary",
      onClick: () => startEditing(generation),
    }),
    actionButton({
      icon: "trash",
      tooltip: t("js.gen.delete", "Eliminar"),
      label: t("js.gen.delete_label", "Eliminar generación"),
      variant: "danger",
      onClick: () => confirmDelete(generation),
    }),
  );

  const cells = [
    createElement("td", { className: "text-nowrap", text: formatDate(generation.created_at) }),
    createElement("td", { text: labels.content_types[generation.content_type] ?? generation.content_type }),
    createElement("td", { text: generation.customer }),
    createElement("td", { className: "d-none d-md-table-cell", text: generation.company }),
    createElement("td", { className: "d-none d-lg-table-cell text-body-secondary small", text: generation.ai_provider }),
    createElement("td", { className: "text-end" }),
  ];
  cells.at(-1).append(actions);
  row.append(...cells);
  return row;
}

function renderHistory() {
  disposeRowTooltips();
  historyView.body.replaceChildren(...historyView.items.map(historyRow));
  historyView.total.textContent = historyView.totalCount || "";
  show(historyView.table, historyView.items.length > 0);
  show(historyView.empty, historyView.items.length === 0);
  show(historyView.more, historyView.items.length < historyView.totalCount);
}

async function loadHistory({ append = false } = {}) {
  show(historyView.error, false);
  historyView.more.disabled = true;
  try {
    const page = await listGenerations({
      limit: HISTORY_PAGE_SIZE,
      offset: append ? historyView.items.length : 0,
      contentType: historyView.filter.value,
    });
    historyView.items = append ? [...historyView.items, ...page.items] : page.items;
    historyView.totalCount = page.total;
    renderHistory();
  } catch (error) {
    historyView.error.textContent = t("js.gen.history_failed", "No se pudo cargar el historial. {message}", { message: error.message });
    show(historyView.error, true);
  } finally {
    historyView.more.disabled = false;
  }
}

historyView.filter.addEventListener("change", () => loadHistory());
historyView.refresh.addEventListener("click", () => loadHistory());
historyView.more.addEventListener("click", () => loadHistory({ append: true }));

loadHistory();
