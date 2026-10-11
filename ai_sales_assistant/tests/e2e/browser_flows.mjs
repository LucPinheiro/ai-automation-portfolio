// End-to-end flows in a real headless Chrome, driven through the DevTools protocol.
// Usage: node browser_flows.mjs <baseUrl> <scenario>   (prints one JSON report)
// Run by tests/e2e/test_browser.py against a throwaway server; no npm dependencies.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

import { testBrowserPids } from "./chrome_processes.mjs";

const [BASE, scenario] = process.argv.slice(2);
const CHROME =
  process.env.CHROME_PATH ??
  [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].find((path) => existsSync(path));
const PORT = 9400 + Math.floor(Math.random() * 400);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let ws;
let nextId = 1;
const pending = new Map();
const events = [];

function send(method, params = {}, timeout = 5000) {
  const id = nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    setTimeout(() => pending.delete(id) && reject(new Error(`timeout: ${method}`)), timeout);
  });
}

// An evaluation sent while the page is switching documents can be dropped by Chrome
// ("timeout" / "context destroyed"): retry it on the new document instead of failing the run.
const TRANSIENT = /timeout: Runtime\.evaluate|context|destroyed|Cannot find default execution context/i;

async function evaluate(expression, attempts = 5) {
  for (let attempt = 1; ; attempt++) {
    try {
      const { result, exceptionDetails } = await send(
        "Runtime.evaluate",
        { expression, awaitPromise: true, returnByValue: true },
        3000,
      );
      if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
      return result.value;
    } catch (error) {
      if (attempt >= attempts || !TRANSIENT.test(String(error))) {
        throw new Error(`${error.message} while evaluating: ${expression.slice(0, 120)}`);
      }
      await sleep(250);
    }
  }
}

async function waitFor(expression, timeout = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      if (await evaluate(expression)) return true;
    } catch {
      // The page is navigating; try again.
    }
    await sleep(100);
  }
  return false;
}

async function waitForEvent(matches, sinceIndex, timeout) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (events.slice(sinceIndex).some(matches)) return true;
    await sleep(100);
  }
  return false;
}

// Loading a page is a GET, so it is safe to repeat. Occasionally the first request of a freshly
// started test Chrome never reaches the local server (seen in the server log: no response logged),
// so if the page has not arrived after 15 s it is requested once more, and that is reported.
// The wait is tied to THIS navigation (its loaderId): a late load event from a previous form
// submission must not be mistaken for it.
async function open(path) {
  for (let attempt = 1; attempt <= 2; attempt++) {
    const before = events.length;
    const navigation = await send("Page.navigate", { url: `${BASE}${path}` }).catch(() => null);
    const loaderId = navigation?.loaderId;
    const arrived = await waitForEvent(
      (event) =>
        event.method === "Page.frameNavigated" &&
        !event.params.frame.parentId &&
        (!loaderId || event.params.frame.loaderId === loaderId),
      before,
      15000,
    );
    if (arrived) break;
    if (attempt === 1) console.error(`[e2e] page ${path} did not load in 15 s; requesting it once more`);
  }
  await waitFor("document.readyState === 'complete'");
  await sleep(300);
}

// A click is not idempotent, so it is never retried. If it submits a form or follows a link, Chrome
// may drop the reply while the page navigates: that lost reply means the click did happen.
async function click(selector) {
  try {
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).click(); true`, 1);
  } catch (error) {
    if (!TRANSIENT.test(String(error))) throw error;
  }
}
const setValue = (id, value) =>
  evaluate(`document.getElementById(${JSON.stringify(id)}).value = ${JSON.stringify(value)}; true`);

async function landedOn(path) {
  return waitFor(`location.pathname === ${JSON.stringify(path)} && document.readyState === 'complete'`);
}

async function pageState() {
  return evaluate(`({
    path: location.pathname,
    search: location.search,
    guestMenu: !!document.getElementById('guest-menu'),
    userMenu: !!document.getElementById('user-menu'),
    generateForm: !!document.getElementById('generate-form'),
    loginError: document.querySelector('#login-form [data-form-error]:not(.d-none)')?.textContent.trim() || null,
    notice: document.querySelector('.alert-info')?.textContent.trim() || null,
    cookieVisibleToJs: document.cookie,
  })`);
}

const apiStatus = (path, method = "GET") =>
  evaluate(`fetch(${JSON.stringify(path)}, { method: ${JSON.stringify(method)} }).then((r) => r.status)`);

// Geometry of the access screen: where the card, the presentation and the footer are.
const layout = () =>
  evaluate(`(() => {
    const box = (selector) => {
      const r = document.querySelector(selector).getBoundingClientRect();
      return { top: r.top + scrollY, left: r.left, width: r.width, bottom: r.bottom + scrollY };
    };
    return {
      card: box(".access-card"),
      aside: box(".access-aside"),
      footer: box(".site-footer"),
      viewportWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      background: getComputedStyle(document.body).backgroundColor,
    };
  })()`);

// --- Scenarios ------------------------------------------------------------------------------------

const scenarios = {
  async "guest-button"() {
    await open("/login");
    await click("#guest-button");
    const arrived = await landedOn("/app");
    return { arrived, ...(await pageState()), me: await evaluate("fetch('/api/v1/auth/me').then((r) => r.json())") };
  },

  async "guest-button-no-js"() {
    await send("Emulation.setScriptExecutionDisabled", { value: true });
    await open("/login");
    await click("#guest-button");
    const arrived = await landedOn("/app");
    return { arrived, ...(await pageState()) };
  },

  async "demo-login"() {
    await open("/login");
    const prefilled = await evaluate(
      "({ identifier: document.getElementById('identifier').value, password: document.getElementById('password').value, hint: document.getElementById('demo-hint')?.textContent.trim() })",
    );
    await click("#login-button");
    const arrived = await landedOn("/app");
    return { prefilled, arrived, ...(await pageState()), me: await evaluate("fetch('/api/v1/auth/me').then((r) => r.json())") };
  },

  async "demo-login-no-js"() {
    await send("Emulation.setScriptExecutionDisabled", { value: true });
    await open("/login");
    await click("#login-button");
    const arrived = await landedOn("/app");
    return { arrived, ...(await pageState()) };
  },

  async "demo-wrong-password"() {
    await open("/login");
    await setValue("password", "not-the-demo-password");
    await click("#login-button");
    await sleep(1500);
    return { ...(await pageState()), me: await apiStatus("/api/v1/auth/me") };
  },

  async "demo-wrong-password-no-js"() {
    await send("Emulation.setScriptExecutionDisabled", { value: true });
    await open("/login");
    await setValue("password", "not-the-demo-password");
    await click("#login-button");
    await sleep(1500);
    return pageState();
  },

  async "guest-generates"() {
    await open("/login");
    await click("#guest-button");
    await landedOn("/app");
    await setValue("customer", "Cliente E2E");
    await setValue("company", "Empresa E2E");
    await setValue("industry", "Logística");
    await setValue("product_or_service", "Software");
    await setValue("customer_needs", "Reducir costes");
    await setValue("salesperson", "Carlos Vila");
    await setValue("customer_email", "cliente@e2e.es");
    // Share buttons next to «Copiar»: disabled until there is a result.
    const shareBefore = await evaluate(`["share-email", "share-whatsapp"].map((id) => {
      const a = document.getElementById(id);
      return { disabled: a.classList.contains("disabled") && a.getAttribute("aria-disabled") === "true", href: a.getAttribute("href") };
    })`);
    // Pricing: typing fires the input events that request the backend preview.
    await evaluate(`for (const [id, value] of [["price", "179"], ["discount_percent", "15"]]) {
      const input = document.getElementById(id);
      input.value = value;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    } true`);
    await waitFor("!document.getElementById('pricing-preview').classList.contains('d-none')", 5000);
    const pricingPreview = await evaluate("document.getElementById('pricing-preview').textContent");
    await click("#generate-button");
    await waitFor("document.getElementById('result-content').textContent.trim().length > 0", 15000);
    await waitFor("document.querySelectorAll('#history-body tr').length > 0", 5000);
    const report = {
      result: await evaluate("document.getElementById('result-content').textContent.trim()"),
      boldRendered: await evaluate("!!document.querySelector('#result-content strong, #result-content h5')"),
      historyRows: await evaluate("document.querySelectorAll('#history-body tr').length"),
      resultError: await evaluate("document.querySelector('#result-error:not(.d-none)')?.textContent ?? null"),
      commercialWarning: await evaluate("document.querySelector('#result-commercial-missing:not(.d-none)')?.textContent ?? null"),
      stored: await evaluate("fetch('/api/v1/generations').then((r) => r.json()).then((j) => j.items[0])"),
      pricingPreview,
      shareBefore,
      share: await evaluate(`(() => {
        const box = (el) => { const r = el.getBoundingClientRect(); return { left: r.left, top: r.top, height: Math.round(r.height) }; };
        const copy = document.getElementById("copy-result");
        const buttons = [...document.getElementById("result-actions").children].map((el) => el.id);
        const link = (id) => {
          const a = document.getElementById(id);
          return { href: a.getAttribute("href"), target: a.target, disabled: a.classList.contains("disabled"),
                   icon: !!a.querySelector("svg"), label: a.getAttribute("aria-label"), box: box(a) };
        };
        return { buttons, copy: box(copy), email: link("share-email"), whatsapp: link("share-whatsapp"),
                 resultText: window.document.getElementById("result-content").innerText.trim() };
      })()`),
    };

    // "Ver": the detail lists the salesperson.
    await click("#history-body tr .history-actions button:nth-child(1)");
    await waitFor("document.getElementById('detail-modal').classList.contains('show')", 5000);
    report.detail = await evaluate("document.getElementById('detail-meta').textContent");
    await evaluate("bootstrap.Modal.getInstance(document.getElementById('detail-modal')).hide(); true");
    await waitFor("!document.getElementById('detail-modal').classList.contains('show')", 5000);

    // "Editar": the form gets the salesperson back.
    await click("#history-body tr .history-actions button:nth-child(2)");
    await waitFor("!document.getElementById('edit-banner').classList.contains('d-none')", 5000);
    report.editSalesperson = await evaluate("document.getElementById('salesperson').value");
    report.editCustomerEmail = await evaluate("document.getElementById('customer_email').value");
    report.editCompany = await evaluate("document.getElementById('salesperson_company').value");
    report.editPrice = await evaluate("document.getElementById('price').value");
    report.editDiscount = await evaluate("document.getElementById('discount_percent').value");
    report.editPreview = await evaluate("document.getElementById('pricing-preview').textContent");
    return report;
  },

  async "missing-terms-warning"() {
    await open("/login");
    await click("#guest-button");
    await landedOn("/app");
    await setValue("customer", "María López");
    await setValue("company", "Pesquera Atlántica S.L.");
    await setValue("industry", "Pesca");
    await setValue("product_or_service", "Contenedores");
    await setValue(
      "customer_needs",
      [
        "E2E-OMIT",
        "Oferta por volumen:",
        "- De 1 a 5 contenedores: precio habitual, sin descuento.",
        "- De 6 a 10 contenedores: 5 % de descuento.",
        "- De 11 a 20 contenedores: 10 % de descuento.",
        "- De 21 a 50 contenedores: 15 % de descuento.",
        "- Más de 50 contenedores: 20 % de descuento.",
      ].join("\n"),
    );
    await click("#generate-button");
    await waitFor("!document.getElementById('result-commercial-missing').classList.contains('d-none')", 15000);
    const report = {
      warning: await evaluate("document.getElementById('result-commercial-missing').textContent"),
      regenerateButton: await evaluate("!!document.getElementById('regenerate-missing')"),
      result: await evaluate("document.getElementById('result-content').textContent"),
    };
    await click("#regenerate-missing");
    await sleep(500);
    await waitFor("!document.getElementById('result-commercial-missing').classList.contains('d-none') && !!document.getElementById('regenerate-missing')", 15000);
    report.afterRegenerate = await evaluate("document.getElementById('result-commercial-missing').textContent.includes('De 6 a 10')");
    await waitFor("document.querySelectorAll('#history-body tr').length > 0", 5000);
    await click("#history-body tr .history-actions button:nth-child(1)");
    await waitFor("document.getElementById('detail-modal').classList.contains('show')", 5000);
    report.detailWarning = await evaluate("document.getElementById('detail-commercial-missing').textContent");
    return report;
  },

  async "guest-logout"() {
    await open("/login");
    await click("#guest-button");
    await landedOn("/app");
    // The guest is asked to confirm, because leaving deletes the guest's generations.
    await evaluate("window.confirm = () => true; document.getElementById('logout-button').click(); true");
    const arrived = await landedOn("/login");
    return { arrived, ...(await pageState()), me: await apiStatus("/api/v1/auth/me"), app: await apiStatus("/api/v1/generations") };
  },

  async "register-logout-login"() {
    const email = `e2e-${Date.now()}@example.com`;
    await open("/register");
    await setValue("name", "Usuaria E2E");
    await setValue("email", email);
    await setValue("password", "e2e-password-1");
    await setValue("password_confirm", "e2e-password-1");
    await click("#register-button");
    const registered = await landedOn("/app");
    const afterRegister = await pageState();

    await evaluate("document.getElementById('logout-button').click(); true");
    const loggedOut = await landedOn("/login");
    const afterLogout = { ...(await pageState()), me: await apiStatus("/api/v1/auth/me") };

    await setValue("identifier", email);
    await setValue("password", "e2e-password-1");
    await click("#login-button");
    const loggedIn = await landedOn("/app");
    return { registered, afterRegister, loggedOut, afterLogout, loggedIn, afterLogin: await pageState() };
  },

  async "login-layout-desktop"() {
    await send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 820, deviceScaleFactor: 1, mobile: false });
    await open("/login");
    return layout();
  },

  async "login-layout-mobile"() {
    await send("Emulation.setDeviceMetricsOverride", { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
    await open("/login");
    return layout();
  },

  async "language-selector"() {
    await open("/login");
    const before = await evaluate("document.querySelector('#language-selector .dropdown-menu').classList.contains('show')");
    await click("#language-selector .lang-switch-toggle");
    await waitFor("document.querySelector('#language-selector .dropdown-menu').classList.contains('show')", 3000);
    return {
      before,
      label: await evaluate("document.querySelector('#language-selector .lang-switch-toggle').textContent.trim()"),
      open: await evaluate("document.querySelector('#language-selector .dropdown-menu').classList.contains('show')"),
      items: await evaluate("[...document.querySelectorAll('#language-selector .dropdown-item')].map((i) => i.textContent.trim())"),
      lang: await evaluate("document.documentElement.lang"),
    };
  },

  async "switch-to-english"() {
    const text = (selector) => evaluate(`document.querySelector(${JSON.stringify(selector)})?.textContent.replace(/\\s+/g, ' ').trim() ?? null`);
    const texts = (selector) =>
      evaluate(`[...document.querySelectorAll(${JSON.stringify(selector)})].map((e) => e.textContent.replace(/\\s+/g, ' ').trim())`);
    const choose = async (code, path) => {
      await click("#language-selector .lang-switch-toggle");
      await waitFor("document.querySelector('#language-selector .dropdown-menu').classList.contains('show')", 3000);
      await click(`#language-selector [data-language="${code}"]`);
      await waitFor(`document.documentElement.lang === ${JSON.stringify(code)} && location.pathname === ${JSON.stringify(path)} && document.readyState === 'complete'`);
      await sleep(300);
    };
    const report = {};

    // Login page: pick EN in the top-right selector.
    await open("/login");
    await choose("en", "/login");
    report.login = {
      lang: await evaluate("document.documentElement.lang"),
      selector: await text("#language-selector .lang-switch-toggle"),
      title: await text("#access-title"),
      submit: await text("#login-button .button-label"),
      guest: await text("#guest-button .button-label"),
      slogan: await text(".access-aside-slogan"),
      footer: await texts(".site-footer a"),
      copyright: await text(".site-footer-copy"),
    };

    // The choice is kept: the guest app opens in English, including the texts set by JavaScript.
    await click("#guest-button");
    await landedOn("/app");
    await waitFor("document.getElementById('history-empty') && !document.getElementById('history-empty').classList.contains('d-none')", 5000);
    await click("#generate-button");
    await waitFor("document.querySelector('[data-error-for=\"customer\"]').textContent !== ''", 3000);
    report.app = {
      lang: await evaluate("document.documentElement.lang"),
      formTitle: await text("#form-title"),
      generate: await text("#generate-button .button-label"),
      guestBadge: await text(".guest-badge"),
      requiredError: await text('[data-error-for="customer"]'),
      historyEmpty: await text("#history-empty"),
      contentType: await text("#content_type option:checked"),
      footer: await texts(".site-footer a"),
    };

    // And back to Spanish from the app header.
    await choose("es", "/app");
    report.back = { lang: await evaluate("document.documentElement.lang"), formTitle: await text("#form-title"), footer: await texts(".site-footer-legal a") };
    return report;
  },

  async "switch-pt-fr"() {
    const text = (selector) => evaluate(`document.querySelector(${JSON.stringify(selector)})?.textContent.replace(/\\s+/g, ' ').trim() ?? null`);
    const texts = (selector) =>
      evaluate(`[...document.querySelectorAll(${JSON.stringify(selector)})].map((e) => e.textContent.replace(/\\s+/g, ' ').trim())`);
    const choose = async (code, path) => {
      await click("#language-selector .lang-switch-toggle");
      await waitFor("document.querySelector('#language-selector .dropdown-menu').classList.contains('show')", 3000);
      await click(`#language-selector [data-language="${code}"]`);
      await waitFor(`document.documentElement.lang === ${JSON.stringify(code)} && location.pathname === ${JSON.stringify(path)} && document.readyState === 'complete'`);
      await sleep(300);
    };
    const loginView = async () => ({
      lang: await evaluate("document.documentElement.lang"),
      selector: await text("#language-selector .lang-switch-toggle"),
      title: await text("#access-title"),
      guest: await text("#guest-button .button-label"),
      footer: await texts(".site-footer a"),
    });
    const appView = async () => {
      await click("#generate-button");
      await waitFor("document.querySelector('[data-error-for=\"customer\"]').textContent !== ''", 3000);
      return {
        lang: await evaluate("document.documentElement.lang"),
        formTitle: await text("#form-title"),
        generate: await text("#generate-button .button-label"),
        requiredError: await text('[data-error-for="customer"]'),
        footer: await texts(".site-footer-legal a"),
      };
    };
    const report = {};

    await open("/login");
    await choose("pt", "/login");
    report.loginPt = await loginView();
    await choose("fr", "/login");
    report.loginFr = await loginView();

    await click("#guest-button");
    await landedOn("/app");
    report.appFr = await appView();
    await choose("pt", "/app");
    report.appPt = await appView();
    return report;
  },

  async "footer-navigation"() {
    const visited = {};
    for (const [text, path] of [["Contacto", "/contacto"], ["Legal", "/legal"], ["Privacidad", "/privacidad"]]) {
      await open("/login");
      await evaluate(`[...document.querySelectorAll('.site-footer a')].find((a) => a.textContent.trim() === ${JSON.stringify(text)}).click(); true`);
      await landedOn(path);
      visited[path] = await evaluate("document.querySelector('h1').textContent.trim()");
    }
    return { visited };
  },

  async "footer-contacts"() {
    await send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 820, deviceScaleFactor: 1, mobile: false });
    await send("Emulation.setFocusEmulationEnabled", { enabled: true });
    const links = `(() => [...document.querySelectorAll('.site-footer a.footer-social-link')].map((a) => {
      const r = a.getBoundingClientRect();
      return { name: a.dataset.footerContact, text: a.textContent.replace(/\\s+/g, ' ').trim(), href: a.getAttribute('href'),
               target: a.target, icon: !!a.querySelector('svg.footer-social-icon'), visible: r.width > 0 && r.height > 0 };
    }))()`;
    const social = (name) => `document.querySelector('.site-footer a[data-footer-contact="${name}"]')`;
    const legal = `[...document.querySelectorAll('.site-footer-legal a')].find((a) => a.textContent.trim() === 'Legal')`;
    const style = (expression) =>
      evaluate(`(() => { const a = ${expression}; const s = getComputedStyle(a), svg = a.querySelector('svg');
                return { bg: s.backgroundColor, border: s.borderTopStyle, color: s.color,
                         ...(svg ? { icon: getComputedStyle(svg).stroke } : {}) }; })()`);
    const hover = async (expression) => {
      const r = await evaluate(`(() => { const r = (${expression}).getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: r.x, y: r.y, button: "none" });
      await sleep(250);
      const result = await style(expression);
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 2, y: 2, button: "none" });
      await sleep(250);
      return result;
    };
    const report = {};

    await open("/login");
    report.login = await evaluate(links);
    // One row on desktop: copyright left, legal links centred, contact links right.
    report.row = await evaluate(`(() => {
      const box = (s) => { const r = document.querySelector(s).getBoundingClientRect(); return { left: r.left, right: r.right, middle: r.top + r.height / 2 }; };
      const inner = box('.site-footer-inner');
      return { inner, copy: box('.site-footer-copy'), legal: box('.site-footer-legal'), social: box('.site-footer-social') };
    })()`);
    await evaluate(`document.querySelector('.site-footer').scrollIntoView({ block: 'end', behavior: 'instant' }); true`);
    await sleep(150);
    report.copyColor = await evaluate("getComputedStyle(document.querySelector('.site-footer-copy')).color");
    report.socialRest = await style(social("github"));
    report.legalRest = await style(legal);
    report.socialHover = await hover(social("github"));
    report.legalHover = await hover(legal);
    await evaluate(`${social("email")}.focus(); true`);
    await sleep(250);
    report.socialFocus = await style(social("email"));

    await click("#guest-button");
    await landedOn("/app");
    report.app = await evaluate(links);
    return report;
  },

  async "app-brand-styles"() {
    await send("Emulation.setFocusEmulationEnabled", { enabled: true });
    await open("/login");
    await click("#guest-button");
    await landedOn("/app");
    await setValue("customer", "Cliente E2E");
    await setValue("company", "Empresa E2E");
    await setValue("industry", "Logística");
    await setValue("product_or_service", "Software");
    await setValue("customer_needs", "Reducir costes");
    await click("#generate-button");
    await waitFor("document.querySelectorAll('#history-body tr').length > 0", 15000);
    await evaluate("document.getElementById('customer').focus(); true");
    await sleep(300);
    return evaluate(`(() => {
      const style = (el) => getComputedStyle(el);
      const actions = document.querySelectorAll("#history-body tr .history-actions button");
      const customer = document.getElementById("customer");
      return {
        generateBg: style(document.getElementById("generate-button")).backgroundColor,
        copyBorder: style(document.getElementById("copy-result")).borderColor,
        badgeBg: style(document.querySelector("#result-meta .badge")).backgroundColor,
        viewColor: style(actions[0]).color,
        editColor: style(actions[1]).color,
        deleteColor: style(actions[2]).color,
        focusBorder: style(customer).borderColor,
        focusShadow: style(customer).boxShadow,
        focused: document.activeElement === customer,
        inputBg: style(customer).backgroundColor,
        pageBg: style(document.body).backgroundColor,
        cardBg: style(document.querySelector(".card")).backgroundColor,
        headerTop: style(document.querySelector(".app-header")).borderTopColor,
      };
    })()`);
  },

  async "dropdown-highlight"() {
    await send("Emulation.setFocusEmulationEnabled", { enabled: true });
    const colours = (expression) =>
      evaluate(`(() => { const s = getComputedStyle(${expression}); return { bg: s.backgroundColor, color: s.color }; })()`);
    const centre = (expression) =>
      evaluate(`(() => { const r = (${expression}).getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
    const mouse = async (type, { x, y }) =>
      send("Input.dispatchMouseEvent", { type, x, y, button: type === "mouseMoved" ? "none" : "left", clickCount: type === "mouseMoved" ? 0 : 1 });
    const hover = async (expression) => {
      await mouse("mouseMoved", await centre(expression));
      await sleep(150);
      return colours(expression);
    };
    const report = {};

    // Language selector (login page): the current language.
    await open("/login");
    await click("#language-selector .lang-switch-toggle");
    await waitFor("document.querySelector('#language-selector .dropdown-menu').classList.contains('show')", 3000);
    report.languageActive = await colours("document.querySelector('#language-selector .dropdown-item.active')");

    // Guest menu (app header): rest, mouse hover, keyboard focus, and the red "Cerrar sesión".
    await click("#guest-button");
    await landedOn("/app");
    await click("#guest-menu .dropdown-toggle");
    await waitFor("document.querySelector('#guest-menu .dropdown-menu').classList.contains('show')", 3000);
    const items = "document.querySelectorAll('#guest-menu a.dropdown-item')";
    report.menuRest = await colours(`${items}[1]`);
    report.menuHover = await hover(`${items}[0]`);
    report.logoutHover = await hover("document.getElementById('logout-button')");
    await mouse("mouseMoved", { x: 2, y: 2 });
    await evaluate(`${items}[1].focus(); true`);
    await sleep(150);
    report.menuFocus = await colours(`${items}[1]`);
    await click("#guest-menu .dropdown-toggle");

    // Native <select> ("Tipo de contenido"): chosen option, another option, and hover in the open list.
    const select = "document.getElementById('content_type')";
    report.baseSelect = await evaluate("CSS.supports('appearance', 'base-select')");
    report.selectAppearance = await evaluate(`getComputedStyle(${select}).appearance`);
    report.optionChecked = await colours(`${select}.options[${select}.selectedIndex]`);
    const other = `[...${select}.options].find((o) => !o.selected)`;
    report.optionRest = await colours(other);
    const point = await centre(select);
    await mouse("mousePressed", point);
    await mouse("mouseReleased", point);
    await waitFor(`${select}.matches(':open')`, 3000);
    report.optionHover = await hover(other);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    report.pickerClosed = await evaluate(`!${select}.matches(':open')`);
    return report;
  },

  async "login-logo-size"() {
    const sizes = {};
    for (const [name, width, mobile] of [["desktop", 1366, false], ["mobile", 375, true]]) {
      await send("Emulation.setDeviceMetricsOverride", { width, height: 800, deviceScaleFactor: 1, mobile });
      await open("/login");
      sizes[name] = await evaluate(`(() => {
        const mark = document.querySelector(".access-brand .brand-mark").getBoundingClientRect();
        return { mark: Math.round(mark.width), wordmark: getComputedStyle(document.querySelector(".access-brand .brand-wordmark")).fontSize,
                 scroll: document.documentElement.scrollWidth <= document.documentElement.clientWidth };
      })()`);
    }
    return sizes;
  },

  async "contact-page"() {
    const geometry = () =>
      evaluate(`(() => {
        const box = (sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return { top: r.top + scrollY, left: r.left, right: r.right }; };
        return { info: box(".contact-info"), form: box(".contact-form-panel"),
                 noScroll: document.documentElement.scrollWidth <= document.documentElement.clientWidth };
      })()`);
    await send("Emulation.setFocusEmulationEnabled", { enabled: true });
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await open("/contacto");
    const desktop = await geometry();
    await evaluate("document.getElementById('contact-name').focus(); true");
    await sleep(200);
    const styles = await evaluate(`({
      button: getComputedStyle(document.getElementById("contact-submit")).backgroundColor,
      buttonText: getComputedStyle(document.getElementById("contact-submit")).textTransform,
      focusBorder: getComputedStyle(document.getElementById("contact-name")).borderColor,
      inputBg: getComputedStyle(document.getElementById("contact-name")).backgroundColor,
      mailto: document.querySelector("#support-email a").getAttribute("href"),
      tel: document.querySelector("#support-phone a").getAttribute("href"),
      badge: document.getElementById("demo-data-badge").textContent.trim(),
      consentInitially: document.getElementById("contact-privacy").checked,
      gdprBelowForm:
        document.getElementById("contact-form").compareDocumentPosition(document.getElementById("contact-gdpr")) ===
        Node.DOCUMENT_POSITION_FOLLOWING,
    })`);

    // Invalid submission: a real form POST, errors next to the fields.
    await setValue("contact-name", "<b>Ana</b>");
    await setValue("contact-email", "no-es-email");
    await click("#contact-submit");
    await waitFor("!!document.getElementById('contact-errors')", 8000);
    const invalid = await evaluate(`({
      nameError: document.getElementById("contact-name-error")?.textContent,
      emailError: document.getElementById("contact-email-error")?.textContent,
      privacyError: document.getElementById("contact-privacy_accepted-error")?.textContent,
      keptName: document.getElementById("contact-name").value,
      demo: !!document.getElementById("contact-demo-result"),
    })`);

    // Valid submission: demo notice, nothing pretends to be sent.
    await setValue("contact-name", "Ana Ruiz");
    await setValue("contact-email", "ana@example.com");
    await evaluate("document.getElementById('contact-category').value = 'api'; true");
    await setValue("contact-subject", "Error 502 al generar");
    await setValue("contact-message", "Al generar un email recibo un error 502 desde esta mañana.");
    // GDPR consent: tick the privacy checkbox with a real click before sending.
    await click("#contact-privacy");
    const consent = await evaluate(`({
      checked: document.getElementById("contact-privacy").checked,
      color: getComputedStyle(document.getElementById("contact-privacy")).backgroundColor,
      errorShown: (() => {
        const error = document.getElementById("contact-privacy_accepted-error");
        return !!error && getComputedStyle(error).display !== "none";
      })(),
    })`);
    await click("#contact-submit");
    await waitFor("!!document.getElementById('contact-demo-result')", 8000);
    const valid = await evaluate(`({
      notice: document.getElementById("contact-demo-result").textContent.trim(),
      cleared: document.getElementById("contact-name").value === "",
      consentAfter: document.getElementById("contact-privacy").checked,
      errors: !!document.getElementById("contact-errors"),
    })`);

    await send("Emulation.setDeviceMetricsOverride", { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
    await open("/contacto");
    const mobile = await geometry();
    return { desktop, mobile, styles, invalid, consent, valid };
  },

  async "protected-app-redirects"() {
    await open("/app");
    await sleep(300);
    return pageState();
  },
};

// --- Runner ---------------------------------------------------------------------------------------

// --- Closing the test browser safely -------------------------------------------------------------
//
// Chrome runs several processes and, on Windows, the one we spawn may only be a launcher, so killing
// it can leave the real browser and its children running. Closing works in this order:
//   1. ask the browser to close itself (Browser.close ends every one of its processes);
//   2. wait for that to happen;
//   3. only if something is still running, terminate exactly those processes that are provably this
//      run's: --user-data-dir equal to this run's own temporary profile folder (chrome_processes.mjs).
// No name patterns or wildcards are ever used, so the user's own Chrome can never match.

const debug = (...args) => process.env.E2E_DEBUG && console.error(`[e2e ${new Date().toISOString().slice(11, 23)}]`, ...args);

async function stopChrome(chrome, profile) {
  debug("closing browser");
  try {
    const { webSocketDebuggerUrl } = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
    const browserSocket = new WebSocket(webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      browserSocket.addEventListener("open", resolve);
      browserSocket.addEventListener("error", reject);
    });
    browserSocket.send(JSON.stringify({ id: 1, method: "Browser.close" }));
  } catch {
    // Already closed or unreachable: the checks below still run.
  }
  // Chrome acknowledges Browser.close at once but, on Windows, takes several seconds to exit.
  // Waiting for that with repeated process queries made every test slow, so: a short grace
  // period, then close the processes that are verifiably this run's, then confirm.
  await Promise.race([new Promise((resolve) => chrome.once("exit", resolve)), sleep(1000)]);
  if (process.platform !== "win32") {
    if (chrome.exitCode === null) chrome.kill();
    return;
  }
  const remaining = testBrowserPids(profile);
  debug(`${remaining.length} process(es) of this run still running`, remaining.join(" "));
  for (const pid of remaining) {
    try {
      process.kill(pid);
      // Always reported (stderr), so every forced close can be audited.
      console.error(`[e2e] closed test process ${pid} (profile ${basename(profile)})`);
    } catch {
      // Exited in the meantime.
    }
  }
  if (remaining.length && process.env.E2E_DEBUG) {
    await sleep(1500); // termination is asynchronous: give it a moment before checking
    debug(`after closing: ${testBrowserPids(profile).length} process(es) left`);
  }
}

async function run() {
  if (!CHROME) throw new Error("Chrome not found (set CHROME_PATH)");
  const profile = mkdtempSync(join(tmpdir(), "e2e-chrome-"));
  const chrome = spawn(CHROME, [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    // Direct connections only: with a fresh profile Chrome otherwise applies the system proxy
    // settings (including auto-detection), and its requests to the local test server can stall
    // before reaching it (the server log showed no request at all from Chrome in those runs).
    "--no-proxy-server",
    // No GPU process and no crash reporter: they were the processes that outlived Browser.close.
    "--disable-gpu",
    "--disable-crash-reporter",
    "about:blank",
  ]);
  try {
    let page;
    // Chrome can be slow to start when the machine is busy: wait up to 30 s.
    for (let i = 0; i < 300 && !page; i++) {
      try {
        const targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
        page = targets.find((t) => t.type === "page");
      } catch {
        await sleep(100);
      }
    }
    if (!page) throw new Error("Chrome did not start");
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve) => ws.addEventListener("open", resolve));
    ws.addEventListener("message", ({ data }) => {
      const message = JSON.parse(data);
      if (message.id && pending.has(message.id)) {
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        message.error ? reject(new Error(message.error.message)) : resolve(message.result);
      } else if (message.method) {
        events.push(message);
      }
    });
    await send("Runtime.enable");
    await send("Network.enable");
    await send("Page.enable");
    await send("Inspector.enable");

    const report = await scenarios[scenario]();
    report.jsErrors = events
      .filter((e) => e.method === "Runtime.exceptionThrown")
      .map((e) => e.params.exceptionDetails.exception?.description ?? e.params.exceptionDetails.text);
    report.failedRequests = events
      .filter((e) => e.method === "Network.responseReceived" && e.params.response.status >= 500)
      .map((e) => `${e.params.response.status} ${e.params.response.url}`);
    console.log(JSON.stringify(report));
  } finally {
    ws?.close();
    await stopChrome(chrome, profile);
    await sleep(300);
    try {
      rmSync(profile, { recursive: true, force: true });
    } catch {
      // Chrome may still hold the profile for a moment.
    }
  }
}

// What the page was doing when the harness failed: dialogs, crashes, last URL, pending requests.
function diagnostics() {
  const finished = new Set(
    events.filter((e) => e.method === "Network.loadingFinished" || e.method === "Network.loadingFailed").map((e) => e.params.requestId),
  );
  return {
    dialogs: events.filter((e) => e.method === "Page.javascriptDialogOpening").map((e) => `${e.params.type}: ${e.params.message}`),
    crashed: events.some((e) => e.method === "Inspector.targetCrashed"),
    lastUrl: events.filter((e) => e.method === "Page.frameNavigated" && !e.params.frame.parentId).map((e) => e.params.frame.url).pop() ?? null,
    pendingRequests: events
      .filter((e) => e.method === "Network.requestWillBeSent" && !finished.has(e.params.requestId))
      .map((e) => `${e.params.request.method} ${e.params.request.url.replace(BASE, "")}`),
  };
}

run()
  .then(() => process.exit(0))
  .catch((error) => {
    console.log(JSON.stringify({ harnessError: String(error), diagnostics: diagnostics() }));
    process.exit(1);
  });
