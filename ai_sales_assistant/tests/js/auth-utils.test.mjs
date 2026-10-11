import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { DEFAULT_AFTER_LOGIN, passwordErrors, resetTokenFrom, safeNextPath } from "../../app/static/js/auth-utils.js";

describe("safeNextPath", () => {
  test("keeps same-site paths", () => {
    assert.equal(safeNextPath("/app"), "/app");
    assert.equal(safeNextPath("/account?tab=1"), "/account?tab=1");
  });

  for (const value of [undefined, null, "", "https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)", "app"]) {
    test(`rejects ${JSON.stringify(value)}`, () => {
      assert.equal(safeNextPath(value), DEFAULT_AFTER_LOGIN);
    });
  }
});

describe("passwordErrors", () => {
  const options = { min: 8, max: 128, field: "password", confirmField: "password_confirm" };

  test("accepts a valid matching password", () => {
    assert.deepEqual(passwordErrors("long-enough", "long-enough", options), {});
  });

  test("reports a short password", () => {
    assert.match(passwordErrors("short", "short", options).password, /al menos 8/);
  });

  test("reports a too long password", () => {
    const long = "x".repeat(129);
    assert.match(passwordErrors(long, long, options).password, /128/);
  });

  test("reports a confirmation mismatch on the confirmation field", () => {
    assert.deepEqual(passwordErrors("long-enough", "different!", options), {
      password_confirm: "Las contraseñas no coinciden.",
    });
  });

  test("passwords are not trimmed", () => {
    assert.ok(passwordErrors("long-enough ", "long-enough", options).password_confirm);
  });
});

describe("resetTokenFrom", () => {
  test("reads the token from the query string", () => {
    assert.equal(resetTokenFrom("?token=abc-123_x"), "abc-123_x");
  });

  test("is empty when missing", () => {
    assert.equal(resetTokenFrom(""), "");
    assert.equal(resetTokenFrom("?other=1"), "");
  });
});
