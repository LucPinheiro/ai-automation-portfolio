import assert from "node:assert/strict";
import { describe, test } from "node:test";

import {
  FORM_FIELDS,
  decimalForInput,
  describeGeneration,
  formValuesFrom,
  normalizeDecimal,
  SHARE_EMAIL_SUBJECT,
  shareLinks,
  toApiPayload,
} from "../../app/static/js/generation-form.js";

const stored = {
  id: 7,
  content_type: "sales_proposal",
  customer: "María López",
  company: "Logística Norte S.L.",
  industry: "Logística",
  product_or_service: "Software de flotas",
  customer_needs: "Reducir costes.",
  price: "49.99",
  discount_percent: "15.00",
  customer_email: "maria@logisticanorte.es",
  salesperson: "Carlos Vila",
  salesperson_company: null,
  language: "es",
  tone: "formal",
  generated_content: "Contenido generado por la IA",
  ai_provider: "ollama",
  ai_model: "llama3.2:3b",
  created_at: "2026-10-07T12:00:00Z",
};

describe("formValuesFrom", () => {
  test("loads the thirteen input fields of the generation, including email, salesperson and pricing", () => {
    assert.deepEqual(formValuesFrom(stored), {
      content_type: "sales_proposal",
      customer: "María López",
      company: "Logística Norte S.L.",
      industry: "Logística",
      product_or_service: "Software de flotas",
      customer_email: "maria@logisticanorte.es",
      customer_needs: "Reducir costes.",
      price: "49,99",
      discount_percent: "15",
      salesperson: "Carlos Vila",
      salesperson_company: "",
      language: "es",
      tone: "formal",
    });
  });

  test("never includes the generated content or server-side fields", () => {
    const values = formValuesFrom(stored);
    for (const field of ["generated_content", "id", "ai_provider", "ai_model", "created_at"]) {
      assert.ok(!(field in values), field);
    }
  });

  test("missing fields become empty strings", () => {
    assert.equal(formValuesFrom({ id: 1 }).customer, "");
  });

  test("an older generation without salesperson loads empty inputs, never a made-up name", () => {
    const values = formValuesFrom({ ...stored, salesperson: null, salesperson_company: null });
    assert.equal(values.salesperson, "");
    assert.equal(values.salesperson_company, "");
  });

  test("FORM_FIELDS does not contain generated_content", () => {
    assert.ok(!FORM_FIELDS.includes("generated_content"));
    assert.equal(new Set(FORM_FIELDS).size, 13);
  });
});

describe("describeGeneration", () => {
  test("uses the content type label when available", () => {
    assert.equal(
      describeGeneration(stored, { sales_proposal: "Propuesta comercial" }),
      "#7 · Propuesta comercial · María López (Logística Norte S.L.)",
    );
  });

  test("falls back to the raw content type", () => {
    assert.match(describeGeneration(stored), /sales_proposal/);
  });
});

describe("pricing inputs (the browser converts, the backend calculates)", () => {
  test("a Spanish decimal comma is converted for the API", () => {
    assert.equal(normalizeDecimal("49,99"), "49.99");
    assert.equal(normalizeDecimal(" 179 "), "179");
    assert.equal(normalizeDecimal("12.5"), "12.5");
    assert.equal(normalizeDecimal(""), "");
    assert.equal(normalizeDecimal(null), "");
  });

  test("anything ambiguous is sent as typed, for the API to reject", () => {
    assert.equal(normalizeDecimal("1.234,56"), "1.234,56");
    assert.equal(normalizeDecimal("-5"), "-5");
    assert.equal(normalizeDecimal("abc"), "abc");
  });

  test("toApiPayload only touches the decimal fields", () => {
    assert.deepEqual(toApiPayload({ customer: "A,B", price: "49,99", discount_percent: "15" }), {
      customer: "A,B",
      price: "49.99",
      discount_percent: "15",
    });
  });

  test("stored values are shown in Spanish format when editing", () => {
    assert.equal(decimalForInput("179.00"), "179");
    assert.equal(decimalForInput("49.99"), "49,99");
    assert.equal(decimalForInput("12.50"), "12,5");
    assert.equal(decimalForInput("100"), "100");
    assert.equal(decimalForInput(null), "");
  });

  test("editing and saving again keeps the same values", () => {
    const values = formValuesFrom(stored);
    const payload = toApiPayload(values);
    assert.equal(payload.price, "49.99");
    assert.equal(payload.discount_percent, "15");
  });
});

describe("shareLinks", () => {
  const text = "Asunto: Propuesta\n\nHola María & equipo: 15 % de descuento. ¿Hablamos?";

  test("mailto: to the customer, with the Kodexia subject and the whole text as body", () => {
    const { email } = shareLinks(text, "maria@logisticanorte.es");
    const url = new URL(email);

    assert.equal(url.protocol, "mailto:");
    assert.equal(url.pathname, "maria@logisticanorte.es");
    assert.equal(url.searchParams.get("subject"), "Propuesta Comercial - Kodexia");
    assert.equal(url.searchParams.get("body"), text);
    assert.equal(SHARE_EMAIL_SUBJECT, "Propuesta Comercial - Kodexia");
  });

  test("without a customer email the mail opens with no recipient", () => {
    assert.ok(shareLinks(text).email.startsWith("mailto:?subject="));
    assert.ok(shareLinks(text, "").email.startsWith("mailto:?subject="));
  });

  test("special characters in the text cannot break the link (encodeURIComponent)", () => {
    const { email, whatsapp } = shareLinks("a&subject=hack\n#x?y", "maria@example.com");
    assert.equal(new URL(email).searchParams.get("subject"), "Propuesta Comercial - Kodexia");
    assert.equal(new URL(whatsapp).searchParams.get("text"), "a&subject=hack\n#x?y");
  });

  test("WhatsApp: wa.me with the encoded text and no number (the user picks the chat)", () => {
    const url = new URL(shareLinks(text, "maria@logisticanorte.es").whatsapp);

    assert.equal(url.origin + url.pathname, "https://wa.me/");
    assert.equal(url.searchParams.get("text"), text);
  });
});
