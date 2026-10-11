import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { ICONS, createIcon } from "../../app/static/js/icons.js";

const SVG_NS = "http://www.w3.org/2000/svg";

// Minimal DOM stand-in that only supports what createIcon uses.
const fakeDocument = {
  createElementNS(namespace, tag) {
    return {
      namespace,
      tag,
      attributes: {},
      children: [],
      setAttribute(name, value) {
        this.attributes[name] = value;
      },
      append(...nodes) {
        this.children.push(...nodes);
      },
    };
  },
};

describe("createIcon", () => {
  for (const name of ["eye", "pencil", "trash"]) {
    test(`${name} is a decorative SVG that inherits the text color`, () => {
      const svg = createIcon(fakeDocument, name);

      assert.equal(svg.namespace, SVG_NS);
      assert.equal(svg.tag, "svg");
      assert.equal(svg.attributes.viewBox, "0 0 16 16");
      assert.equal(svg.attributes.fill, "currentColor");
      assert.equal(svg.attributes["aria-hidden"], "true");
      assert.equal(svg.attributes.focusable, "false");
      assert.deepEqual(
        svg.children.map((path) => [path.namespace, path.tag, path.attributes.d]),
        ICONS[name].map((d) => [SVG_NS, "path", d]),
      );
    });
  }

  test("unknown icons fail loudly", () => {
    assert.throws(() => createIcon(fakeDocument, "rocket"), /Unknown icon: rocket/);
  });

  test("icons are plain path data, with no markup that could be injected", () => {
    for (const paths of Object.values(ICONS)) {
      for (const d of paths) assert.match(d, /^[MmLlHhVvCcSsQqTtAaZz0-9.,\s-]+$/);
    }
  });
});
