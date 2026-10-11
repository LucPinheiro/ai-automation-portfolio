// Minimal, safe Markdown renderer for AI-generated content.
//
// Safety by construction: the text is parsed into plain data (blocks and inline tokens) and the DOM
// is built only with createElement/createTextNode. Model output is never interpreted as HTML, so
// tags such as <script> or <img onerror> are shown as literal text. Links are not turned into <a>.
//
// parseMarkdown/toPlainText/findPlaceholders are pure (no DOM) so they can be tested with Node.

const HEADING = /^(#{1,6})\s+(.+?)\s*#*\s*$/;
const BOLD_LINE_HEADING = /^(?:\*\*|__)([^*_]+?)(?:\*\*|__):?\s*$/;
const LIST_ITEM = /^(\s*)(?:([-*+•])|(\d{1,3})[.)])\s+(.*)$/;
const HORIZONTAL_RULE = /^\s*([-*_])(?:\s*\1){2,}\s*$/;
const INDENT_FOR_NESTING = 2;

// Order matters: bold before italic, links before placeholders.
const INLINE =
  /\*\*(.+?)\*\*|__(.+?)__|`([^`\n]+)`|\[([^[\]\n]{1,80})\]\(([^()\s]+)\)|\[([^[\]\n]{1,80})\](?!\()|\*(?![\s*])([^*\n]+?)(?<!\s)\*/g;

export function parseInline(text) {
  const tokens = [];
  let last = 0;
  for (const match of text.matchAll(INLINE)) {
    const [whole, bold, boldAlt, code, linkText, linkUrl, placeholder, italic] = match;
    if (match.index > last) tokens.push({ type: "text", text: text.slice(last, match.index) });
    if (bold !== undefined || boldAlt !== undefined) {
      tokens.push({ type: "strong", children: parseInline(bold ?? boldAlt) });
    } else if (code !== undefined) {
      tokens.push({ type: "code", text: code });
    } else if (linkText !== undefined) {
      tokens.push({ type: "text", text: `${linkText} (${linkUrl})` });
    } else if (placeholder !== undefined) {
      tokens.push({ type: "placeholder", text: `[${placeholder}]` });
    } else {
      tokens.push({ type: "em", children: parseInline(italic) });
    }
    last = match.index + whole.length;
  }
  if (last < text.length) tokens.push({ type: "text", text: text.slice(last) });
  return tokens;
}

function listItemFrom(match) {
  const [, indent, bullet, number, text] = match;
  return { indent: indent.replace(/\t/g, "    ").length, ordered: bullet === undefined, number: Number(number), text };
}

function parseList(lines, start) {
  const first = listItemFrom(lines[start].match(LIST_ITEM));
  const list = { type: "list", ordered: first.ordered, start: first.ordered ? first.number : 1, items: [] };
  let i = start;

  while (i < lines.length) {
    const line = lines[i];
    const match = line.match(LIST_ITEM);

    if (!line.trim()) {
      // A blank line inside a list only continues it when the next line is another item.
      const next = lines[i + 1]?.match(LIST_ITEM);
      if (next && listItemFrom(next).ordered === list.ordered) {
        i += 1;
        continue;
      }
      break;
    }

    if (match && !HORIZONTAL_RULE.test(line)) {
      const item = listItemFrom(match);
      const parent = list.items.at(-1);
      if (item.indent >= INDENT_FOR_NESTING && parent) {
        parent.children ??= { type: "list", ordered: item.ordered, start: item.number || 1, items: [] };
        parent.children.items.push({ inlines: parseInline(item.text), children: null });
      } else if (item.ordered !== list.ordered) {
        break;
      } else {
        list.items.push({ inlines: parseInline(item.text), children: null });
      }
      i += 1;
      continue;
    }

    // Indented text continues the previous item; anything else ends the list.
    const parent = list.items.at(-1);
    if (/^\s{2,}\S/.test(line) && parent) {
      const target = parent.children?.items.at(-1) ?? parent;
      target.inlines.push({ type: "text", text: " " }, ...parseInline(line.trim()));
      i += 1;
      continue;
    }
    break;
  }
  return { block: list, next: i };
}

export function parseMarkdown(text) {
  const lines = String(text ?? "").replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let paragraph = null;
  let i = 0;

  const closeParagraph = () => {
    if (paragraph) blocks.push(paragraph);
    paragraph = null;
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    let match;

    if (!trimmed) {
      closeParagraph();
      i += 1;
    } else if (HORIZONTAL_RULE.test(line)) {
      closeParagraph();
      blocks.push({ type: "hr" });
      i += 1;
    } else if ((match = trimmed.match(HEADING))) {
      closeParagraph();
      blocks.push({ type: "heading", level: Math.min(match[1].length, 3), inlines: parseInline(match[2]) });
      i += 1;
    } else if ((match = trimmed.match(BOLD_LINE_HEADING))) {
      closeParagraph();
      blocks.push({ type: "heading", level: 3, inlines: parseInline(match[1].trim().replace(/:$/, "")) });
      i += 1;
    } else if (LIST_ITEM.test(line)) {
      closeParagraph();
      const { block, next } = parseList(lines, i);
      blocks.push(block);
      i = next;
    } else {
      paragraph ??= { type: "paragraph", lines: [] };
      paragraph.lines.push(parseInline(trimmed));
      i += 1;
    }
  }
  closeParagraph();
  return blocks;
}

// --- Plain text (used by the Copy button) -------------------------------------

function inlineText(tokens) {
  return tokens.map((token) => (token.children ? inlineText(token.children) : token.text)).join("");
}

function listText(list, depth = 0) {
  const indent = "  ".repeat(depth);
  return list.items
    .map((item, index) => {
      const marker = list.ordered ? `${list.start + index}.` : depth === 0 ? "•" : "-";
      const line = `${indent}${marker} ${inlineText(item.inlines)}`;
      return item.children ? `${line}\n${listText(item.children, depth + 1)}` : line;
    })
    .join("\n");
}

export function toPlainText(blocks) {
  return blocks
    .map((block) => {
      switch (block.type) {
        case "heading":
          return inlineText(block.inlines);
        case "paragraph":
          return block.lines.map(inlineText).join("\n");
        case "list":
          return listText(block);
        default:
          return "———";
      }
    })
    .join("\n\n");
}

// --- Placeholders ---------------------------------------------------------------

function collectPlaceholders(tokens, found) {
  for (const token of tokens) {
    if (token.type === "placeholder") found.add(token.text);
    if (token.children) collectPlaceholders(token.children, found);
  }
}

function collectFromList(list, found) {
  for (const item of list.items) {
    collectPlaceholders(item.inlines, found);
    if (item.children) collectFromList(item.children, found);
  }
}

export function findPlaceholders(blocks) {
  const found = new Set();
  for (const block of blocks) {
    if (block.type === "heading") collectPlaceholders(block.inlines, found);
    if (block.type === "paragraph") block.lines.forEach((line) => collectPlaceholders(line, found));
    if (block.type === "list") collectFromList(block, found);
  }
  return [...found];
}

// --- DOM rendering -----------------------------------------------------------------

const HEADING_TAGS = { 1: "h3", 2: "h4", 3: "h5" };

function appendInlines(doc, parent, tokens, options) {
  for (const token of tokens) {
    if (token.type === "text") {
      parent.append(doc.createTextNode(token.text));
    } else if (token.type === "placeholder") {
      if (options.highlightPlaceholders) {
        const mark = doc.createElement("mark");
        mark.className = "md-placeholder";
        mark.textContent = token.text;
        parent.append(mark);
      } else {
        parent.append(doc.createTextNode(token.text));
      }
    } else if (token.type === "code") {
      const code = doc.createElement("code");
      code.textContent = token.text;
      parent.append(code);
    } else {
      const element = doc.createElement(token.type === "strong" ? "strong" : "em");
      appendInlines(doc, element, token.children, options);
      parent.append(element);
    }
  }
}

function renderList(doc, list, options) {
  const element = doc.createElement(list.ordered ? "ol" : "ul");
  if (list.ordered && list.start !== 1) element.setAttribute("start", String(list.start));
  for (const item of list.items) {
    const li = doc.createElement("li");
    appendInlines(doc, li, item.inlines, options);
    if (item.children) li.append(renderList(doc, item.children, options));
    element.append(li);
  }
  return element;
}

function renderBlock(doc, block, options) {
  switch (block.type) {
    case "heading": {
      const heading = doc.createElement(HEADING_TAGS[block.level]);
      heading.className = `md-heading md-h${block.level}`;
      appendInlines(doc, heading, block.inlines, options);
      return heading;
    }
    case "paragraph": {
      const paragraph = doc.createElement("p");
      block.lines.forEach((line, index) => {
        if (index > 0) paragraph.append(doc.createElement("br"));
        appendInlines(doc, paragraph, line, options);
      });
      return paragraph;
    }
    case "list":
      return renderList(doc, block, options);
    default:
      return doc.createElement("hr");
  }
}

/** Replace the container's children with the rendered blocks. */
export function renderMarkdown(container, blocks, { highlightPlaceholders = true } = {}) {
  const doc = container.ownerDocument;
  container.replaceChildren(...blocks.map((block) => renderBlock(doc, block, { highlightPlaceholders })));
}
