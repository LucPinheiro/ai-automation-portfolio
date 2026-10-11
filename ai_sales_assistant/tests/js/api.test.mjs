import assert from "node:assert/strict";
import { afterEach, describe, test } from "node:test";

import {
  ApiError,
  changePassword,
  deleteGeneration,
  forgotPassword,
  login,
  logout,
  register,
  resetPassword,
  saveGeneration,
  setUnauthorizedHandler,
  startGuest,
  updateGeneration,
} from "../../app/static/js/api.js";

const realFetch = globalThis.fetch;
let calls = [];

// Replaces fetch with a canned response and records each request.
function mockFetch(status, body = null) {
  calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, ...options });
    return new Response(body === null ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };
}

const data = { content_type: "commercial_email", customer: "Ana" };

afterEach(() => {
  globalThis.fetch = realFetch;
  setUnauthorizedHandler(() => {});
});

describe("updateGeneration", () => {
  test("sends a PUT with the form data to the generation URL", async () => {
    mockFetch(200, { id: 5, generated_content: "Nuevo" });

    const result = await updateGeneration(5, data);

    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "/api/v1/generations/5");
    assert.equal(calls[0].method, "PUT");
    assert.deepEqual(JSON.parse(calls[0].body), data);
    assert.equal(result.generated_content, "Nuevo");
  });

  test("a 404 becomes a friendly not_found error", async () => {
    mockFetch(404, { error: { code: "not_found", message: "Generation 5 was not found.", details: [] } });

    await assert.rejects(updateGeneration(5, data), (error) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, 404);
      assert.equal(error.code, "not_found");
      assert.match(error.message, /ya no existe/);
      return true;
    });
  });

  test("a 422 keeps the field details", async () => {
    const details = [{ field: "customer", message: "String should have at least 1 character", type: "string_too_short" }];
    mockFetch(422, { error: { code: "validation_error", message: "Invalid", details } });

    await assert.rejects(updateGeneration(5, data), (error) => {
      assert.equal(error.code, "validation_error");
      assert.deepEqual(error.details, details);
      return true;
    });
  });

  test("a provider failure (502) is reported in Spanish", async () => {
    mockFetch(502, { error: { code: "ai_provider_error", message: "x", details: [] } });

    await assert.rejects(updateGeneration(5, data), /proveedor de IA/);
  });
});

describe("saveGeneration", () => {
  test("creates with POST /generate when not editing", async () => {
    mockFetch(201, { id: 1 });

    await saveGeneration(data);

    assert.equal(calls[0].url, "/api/v1/generate");
    assert.equal(calls[0].method, "POST");
  });

  test("regenerates with PUT when editing", async () => {
    mockFetch(200, { id: 9 });

    await saveGeneration(data, 9);

    assert.equal(calls[0].url, "/api/v1/generations/9");
    assert.equal(calls[0].method, "PUT");
  });
});

describe("deleteGeneration", () => {
  test("sends a DELETE and accepts an empty 204", async () => {
    mockFetch(204);

    assert.equal(await deleteGeneration(3), undefined);
    assert.equal(calls[0].url, "/api/v1/generations/3");
    assert.equal(calls[0].method, "DELETE");
  });

  test("a 404 is rejected with not_found", async () => {
    mockFetch(404, { error: { code: "not_found", message: "x", details: [] } });

    await assert.rejects(deleteGeneration(3), (error) => error.code === "not_found");
  });

  test("a network failure is reported as such", async () => {
    globalThis.fetch = async () => {
      throw new TypeError("Failed to fetch");
    };

    await assert.rejects(deleteGeneration(3), (error) => error.code === "network_error");
  });
});

describe("authentication calls", () => {
  const cases = [
    ["register", register, "/api/v1/auth/register"],
    ["login", login, "/api/v1/auth/login"],
    ["changePassword", changePassword, "/api/v1/auth/change-password"],
    ["forgotPassword", forgotPassword, "/api/v1/auth/forgot-password"],
    ["resetPassword", resetPassword, "/api/v1/auth/reset-password"],
  ];

  for (const [name, call, url] of cases) {
    test(`${name} POSTs JSON to ${url} relying on the cookie, not on a token`, async () => {
      mockFetch(200, {});

      await call({ email: "a@example.com" });

      assert.equal(calls[0].url, url);
      assert.equal(calls[0].method, "POST");
      assert.equal(calls[0].credentials, "same-origin");
      assert.ok(!("Authorization" in calls[0].headers));
      assert.deepEqual(JSON.parse(calls[0].body), { email: "a@example.com" });
    });
  }

  test("logout POSTs without a body", async () => {
    mockFetch(204);

    await logout();

    assert.equal(calls[0].url, "/api/v1/auth/logout");
    assert.equal(calls[0].method, "POST");
    assert.equal(calls[0].body, undefined);
  });

  test("wrong credentials give a friendly message and do not trigger the session handler", async () => {
    let redirected = false;
    setUnauthorizedHandler(() => {
      redirected = true;
    });
    mockFetch(401, { error: { code: "invalid_credentials", message: "x", details: [] } });

    await assert.rejects(login({}), /Usuario o contraseña incorrectos/);
    assert.equal(redirected, false);
  });

  test("duplicate email is reported in Spanish", async () => {
    mockFetch(409, { error: { code: "email_already_registered", message: "x", details: [] } });

    await assert.rejects(register({}), /Ya existe una cuenta con ese email/);
  });

  test("an invalid reset link is reported in Spanish", async () => {
    mockFetch(400, { error: { code: "invalid_or_expired_token", message: "x", details: [] } });

    await assert.rejects(resetPassword({}), /no es válido o ha caducado/);
  });
});

describe("expired session", () => {
  test("a 401 not_authenticated calls the unauthorized handler", async () => {
    let calledWith = 0;
    setUnauthorizedHandler(() => {
      calledWith += 1;
    });
    mockFetch(401, { error: { code: "not_authenticated", message: "x", details: [] } });

    await assert.rejects(saveGeneration({}), (error) => error.code === "not_authenticated");
    assert.equal(calledWith, 1);
  });

  test("a CSRF rejection is explained", async () => {
    mockFetch(403, { error: { code: "csrf_failed", message: "x", details: [] } });

    await assert.rejects(saveGeneration({}), /bloqueado por seguridad/);
  });
});

describe("guest mode", () => {
  test("startGuest asks the backend for a guest session and stores nothing in the browser", async () => {
    mockFetch(201, { id: 9, is_guest: true });

    const user = await startGuest();

    assert.equal(calls[0].url, "/api/v1/auth/guest");
    assert.equal(calls[0].method, "POST");
    assert.equal(calls[0].credentials, "same-origin");
    assert.equal(calls[0].body, undefined);
    assert.equal(user.is_guest, true);
    assert.equal(typeof globalThis.localStorage, "undefined");
  });

  test("the guest limit is explained", async () => {
    mockFetch(403, { error: { code: "guest_quota_exceeded", message: "x", details: [] } });

    await assert.rejects(saveGeneration({}), /límite de generaciones del modo invitado/);
  });

  test("guest restrictions and a disabled guest mode are explained", async () => {
    mockFetch(403, { error: { code: "guest_not_allowed", message: "x", details: [] } });
    await assert.rejects(changePassword({}), /cuenta registrada/);

    mockFetch(403, { error: { code: "guest_mode_disabled", message: "x", details: [] } });
    await assert.rejects(startGuest(), /invitado no está disponible/);
  });

  test("a taken username is reported in Spanish", async () => {
    mockFetch(409, { error: { code: "username_already_taken", message: "x", details: [] } });

    await assert.rejects(register({}), /nombre de usuario ya está en uso/);
  });
});
