// Run with: node --test tests/js   (also run from pytest by tests/test_web.py)
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { findPlaceholders, parseInline, parseMarkdown, renderMarkdown, toPlainText } from "../../app/static/js/markdown.js";

// Minimal DOM stand-in: records elements and text nodes, and has no way to parse HTML.
class FakeNode {
  constructor(doc, tag) {
    this.ownerDocument = doc;
    this.tag = tag;
    this.children = [];
    this.attributes = {};
    this.className = "";
  }
  append(...nodes) {
    this.children.push(...nodes);
  }
  replaceChildren(...nodes) {
    this.children = nodes;
  }
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
  set textContent(value) {
    this.children = [{ text: value }];
  }
}

const fakeDocument = {
  createElement: (tag) => new FakeNode(fakeDocument, tag),
  createTextNode: (text) => ({ text }),
};

function render(markdown, options) {
  const container = new FakeNode(fakeDocument, "div");
  renderMarkdown(container, parseMarkdown(markdown), options);
  return container;
}

function tags(node) {
  return (node.children ?? []).flatMap((child) => (child.tag ? [child.tag, ...tags(child)] : []));
}

function texts(node) {
  return (node.children ?? []).flatMap((child) => (child.tag ? texts(child) : [child.text]));
}

describe("parseMarkdown", () => {
  test("headings keep a three-level hierarchy", () => {
    const blocks = parseMarkdown("# Uno\n## Dos\n### Tres\n#### Cuatro");
    assert.deepEqual(
      blocks.map((block) => [block.type, block.level]),
      [["heading", 1], ["heading", 2], ["heading", 3], ["heading", 3]],
    );
  });

  test("a line that is only bold text is a heading", () => {
    const [heading, paragraph] = parseMarkdown("**Beneficios esperados:**\nTexto con **negrita** dentro.");
    assert.equal(heading.type, "heading");
    assert.deepEqual(heading.inlines, [{ type: "text", text: "Beneficios esperados" }]);
    assert.equal(paragraph.type, "paragraph");
  });

  test("bullet lists, including a nested level and blank lines between items", () => {
    const [list] = parseMarkdown("* uno\n\n- dos\n  - dos.a\n+ tres");
    assert.equal(list.type, "list");
    assert.equal(list.ordered, false);
    assert.equal(list.items.length, 3);
    assert.equal(list.items[1].children.items.length, 1);
  });

  test("ordered lists keep their start number", () => {
    const [list] = parseMarkdown("3. tres\n4) cuatro");
    assert.equal(list.ordered, true);
    assert.equal(list.start, 3);
    assert.equal(list.items.length, 2);
  });

  test("blank lines separate paragraphs and single newlines are kept as line breaks", () => {
    const blocks = parseMarkdown("Estimada María,\n\nPrimera línea\nsegunda línea\n\nUn saludo,\n[Your name]");
    assert.deepEqual(
      blocks.map((block) => [block.type, block.lines.length]),
      [["paragraph", 1], ["paragraph", 2], ["paragraph", 2]],
    );
  });

  test("horizontal rules are not mistaken for list items", () => {
    assert.deepEqual(parseMarkdown("---\n* * *").map((block) => block.type), ["hr", "hr"]);
  });

  test("handles empty and Windows line endings", () => {
    assert.deepEqual(parseMarkdown(""), []);
    assert.equal(parseMarkdown("a\r\nb").at(0).lines.length, 2);
  });
});

describe("parseInline", () => {
  test("bold, italic and code", () => {
    assert.deepEqual(parseInline("**a** *b* `c` __d__"), [
      { type: "strong", children: [{ type: "text", text: "a" }] },
      { type: "text", text: " " },
      { type: "em", children: [{ type: "text", text: "b" }] },
      { type: "text", text: " " },
      { type: "code", text: "c" },
      { type: "text", text: " " },
      { type: "strong", children: [{ type: "text", text: "d" }] },
    ]);
  });

  test("an asterisk surrounded by spaces is not italic", () => {
    assert.deepEqual(parseInline("2 * 3 * 4"), [{ type: "text", text: "2 * 3 * 4" }]);
  });

  test("links become plain text with the URL, never an anchor", () => {
    assert.ok(parseInline("[clic](javascript:alert(1))").every((token) => token.type === "text"));
    assert.deepEqual(parseInline("[web](https://example.com)"), [{ type: "text", text: "web (https://example.com)" }]);
  });

  test("square-bracket placeholders are detected", () => {
    assert.deepEqual(parseInline("Un saludo, [Your name]"), [
      { type: "text", text: "Un saludo, " },
      { type: "placeholder", text: "[Your name]" },
    ]);
  });
});

describe("safety", () => {
  test("HTML in the model output is rendered as literal text", () => {
    const payload = '<script>alert(1)</script> <img src=x onerror="alert(2)"> **<b>hola</b>**';
    const container = render(payload);

    assert.deepEqual(tags(container), ["p", "strong"]);
    assert.equal(texts(container).join(""), '<script>alert(1)</script> <img src=x onerror="alert(2)"> <b>hola</b>');
  });

  test("only a fixed set of elements can be produced", () => {
    const container = render("# T\n**H**\n\n* a *b* `c` [X]\n1. d\n\n---\nl1\nl2");
    const allowed = new Set(["h3", "h4", "h5", "p", "br", "ul", "ol", "li", "strong", "em", "code", "mark", "hr"]);
    for (const tag of tags(container)) assert.ok(allowed.has(tag), tag);
  });
});

describe("rendering", () => {
  test("produces semantic elements", () => {
    const container = render("## Propuesta\n\nTexto **clave**.\n\n- uno\n- dos");
    assert.deepEqual(tags(container), ["h4", "p", "strong", "ul", "li", "li"]);
  });

  test("placeholders are highlighted only when requested", () => {
    assert.ok(tags(render("Firma: [Your name]")).includes("mark"));
    assert.ok(!tags(render("Firma: [Your name]", { highlightPlaceholders: false })).includes("mark"));
  });
});

describe("toPlainText", () => {
  test("removes Markdown syntax and keeps structure", () => {
    const markdown = "## **Beneficios**\n\nTexto con **negrita** y *cursiva*.\n\n* uno\n  * uno.a\n* dos\n\n1. primero\n2. segundo";
    assert.equal(
      toPlainText(parseMarkdown(markdown)),
      "Beneficios\n\nTexto con negrita y cursiva.\n\n• uno\n  - uno.a\n• dos\n\n1. primero\n2. segundo",
    );
  });

  test("keeps email line breaks and placeholders", () => {
    assert.equal(toPlainText(parseMarkdown("Un saludo,\n[Your name]")), "Un saludo,\n[Your name]");
  });
});

describe("findPlaceholders", () => {
  test("returns each placeholder once, in order", () => {
    const blocks = parseMarkdown("**[Título]**\n\nHola [Your name]\n\n- [Your name] y [Your position]");
    assert.deepEqual(findPlaceholders(blocks), ["[Título]", "[Your name]", "[Your position]"]);
  });
});
