/* Client-side implementation of the `al_tree_select` custom datatype.
 *
 * This file is not loaded with a <script> tag. It is read at import time by
 * al_tree_select.py and handed to docassemble as the CustomDataType's
 * `javascript`, which docassemble evaluates once per page load. That means a
 * developer only has to write `datatype: al_tree_select` -- there is nothing to
 * include and no `script:` block to copy.
 *
 * The widget is deliberately built out of ordinary <details>/<summary>
 * disclosure elements and ordinary <input type="checkbox"> controls, so that
 * keyboard support, screen reader support, and browser find-in-page all work
 * without any ARIA tree/treeitem bookkeeping.
 *
 * The docassemble <input> stays in the DOM and holds a JSON array of the
 * selected keys. That is what gets POSTed, and what ALTreeSelect.transform()
 * turns into a DADict on the server.
 */

(function () {
  "use strict";

  // Replaced with the contents of al_tree_select.css by al_tree_select.py.
  var AL_TREE_CSS = "__AL_TREE_SELECT_CSS__";

  var STYLE_ID = "al-tree-select-styles";
  var idCounter = 0;

  /* ------------------------------------------------------------------ *
   * Translatable strings
   *
   * Resolution order for every string:
   *   1. a per-field `data-al...` attribute (a mako_parameter, so the
   *      developer can write `${ word("Filter choices") }`)
   *   2. window.alTreeSelectStrings, which an interview can set once in a
   *      `script:` block to translate every tree on the site
   *   3. the English default below
   * ------------------------------------------------------------------ */

  var DEFAULT_STRINGS = {
    searchLabel: "Filter choices",
    searchPlaceholder: "Type to filter",
    expandAll: "Expand all",
    collapseAll: "Collapse all",
    clearAll: "Clear all",
    selectAllLabel: "Select all in %s",
    noResults: "No choices match your filter.",
    resultsFound: "%d of %d choices match your filter.",
    filterCleared: "Filter cleared. Showing all %d choices.",
    selectedCount: "%d selected",
    nothingSelected: "Nothing selected yet",
    removeSelection: "Remove %s",
    groupSelectedCount: "%d selected in this group",
    minMessage: "Please choose at least %d.",
    maxMessage: "Please choose no more than %d.",
  };

  function fmt(template, args) {
    var i = 0;
    return String(template).replace(/%[ds]/g, function () {
      var value = args[i];
      i += 1;
      return value === undefined ? "" : String(value);
    });
  }

  function str(ctx, name) {
    var overrides = window.alTreeSelectStrings || {};
    var value = ctx.strings[name];
    if (value === undefined || value === null || value === "") {
      value = overrides[name];
    }
    if (value === undefined || value === null || value === "") {
      value = DEFAULT_STRINGS[name];
    }
    return fmt(value, Array.prototype.slice.call(arguments, 2));
  }

  /* ------------------------------------------------------------------ *
   * Reading the choices out of the DOM
   *
   * docassemble writes custom datatype parameters into `data-` attributes by
   * calling str() on them, so a YAML `choices:` block arrives as a Python
   * literal rather than as JSON. Anything computed with `code:` arrives the
   * same way. We accept JSON first (which is what you get from
   * `${ json.dumps(...) }`) and fall back to a small parser for the Python
   * literal subset that YAML can produce.
   * ------------------------------------------------------------------ */

  function parsePythonLiteral(text) {
    var pos = 0;

    function fail(message) {
      throw new SyntaxError(
        "al_tree_select: " + message + " at position " + pos,
      );
    }

    function skipSpace() {
      while (pos < text.length && /\s/.test(text.charAt(pos))) {
        pos += 1;
      }
    }

    function parseString() {
      var quote = text.charAt(pos);
      pos += 1;
      var out = "";
      while (pos < text.length) {
        var ch = text.charAt(pos);
        if (ch === "\\") {
          pos += 1;
          var esc = text.charAt(pos);
          pos += 1;
          if (esc === "n") {
            out += "\n";
          } else if (esc === "t") {
            out += "\t";
          } else if (esc === "r") {
            out += "\r";
          } else if (esc === "a") {
            out += "\x07";
          } else if (esc === "b") {
            out += "\b";
          } else if (esc === "f") {
            out += "\f";
          } else if (esc === "v") {
            out += "\v";
          } else if (esc === "0") {
            out += "\0";
          } else if (esc === "x" || esc === "u" || esc === "U") {
            var width = esc === "x" ? 2 : esc === "u" ? 4 : 8;
            var hex = text.substr(pos, width);
            pos += width;
            out += String.fromCodePoint(parseInt(hex, 16));
          } else if (esc === "\n") {
            // line continuation; contributes nothing
          } else {
            out += esc;
          }
        } else if (ch === quote) {
          pos += 1;
          return out;
        } else {
          out += ch;
          pos += 1;
        }
      }
      fail("unterminated string");
    }

    function parseSequence(closer) {
      pos += 1;
      var out = [];
      skipSpace();
      if (text.charAt(pos) === closer) {
        pos += 1;
        return out;
      }
      while (pos < text.length) {
        out.push(parseValue());
        skipSpace();
        var ch = text.charAt(pos);
        if (ch === ",") {
          pos += 1;
          skipSpace();
          if (text.charAt(pos) === closer) {
            pos += 1;
            return out;
          }
        } else if (ch === closer) {
          pos += 1;
          return out;
        } else {
          fail("expected ',' or '" + closer + "'");
        }
      }
      fail("unterminated sequence");
    }

    function parseBraced() {
      pos += 1;
      skipSpace();
      if (text.charAt(pos) === "}") {
        pos += 1;
        return {};
      }
      var first = parseValue();
      skipSpace();
      if (text.charAt(pos) !== ":") {
        // A Python set literal. Nothing we support uses one, but treat it as a
        // list rather than blowing up.
        var members = [first];
        while (text.charAt(pos) === ",") {
          pos += 1;
          skipSpace();
          if (text.charAt(pos) === "}") {
            break;
          }
          members.push(parseValue());
          skipSpace();
        }
        if (text.charAt(pos) === "}") {
          pos += 1;
        }
        return members;
      }
      var out = {};
      pos += 1;
      out[String(first)] = parseValue();
      skipSpace();
      while (pos < text.length) {
        var ch = text.charAt(pos);
        if (ch === ",") {
          pos += 1;
          skipSpace();
          if (text.charAt(pos) === "}") {
            pos += 1;
            return out;
          }
          var key = parseValue();
          skipSpace();
          if (text.charAt(pos) !== ":") {
            fail("expected ':'");
          }
          pos += 1;
          out[String(key)] = parseValue();
          skipSpace();
        } else if (ch === "}") {
          pos += 1;
          return out;
        } else {
          fail("expected ',' or '}'");
        }
      }
      fail("unterminated dict");
    }

    function parseValue() {
      skipSpace();
      var ch = text.charAt(pos);
      if (ch === "'" || ch === '"') {
        return parseString();
      }
      if (ch === "[") {
        return parseSequence("]");
      }
      if (ch === "(") {
        return parseSequence(")");
      }
      if (ch === "{") {
        return parseBraced();
      }
      var rest = text.slice(pos);
      var word = /^(True|False|None|true|false|null)\b/.exec(rest);
      if (word) {
        pos += word[0].length;
        if (word[0] === "True" || word[0] === "true") {
          return true;
        }
        if (word[0] === "False" || word[0] === "false") {
          return false;
        }
        return null;
      }
      var number = /^-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/.exec(rest);
      if (number) {
        pos += number[0].length;
        return parseFloat(number[0]);
      }
      fail("unexpected character " + JSON.stringify(ch));
    }

    var result = parseValue();
    skipSpace();
    if (pos < text.length) {
      fail("trailing characters");
    }
    return result;
  }

  function parseChoiceData(raw) {
    if (raw === undefined || raw === null || String(raw).trim() === "") {
      return null;
    }
    var text = String(raw).trim();
    try {
      return JSON.parse(text);
    } catch (jsonError) {
      return parsePythonLiteral(text);
    }
  }

  /* ------------------------------------------------------------------ *
   * Normalizing choices into a tree
   *
   * Kept deliberately in step with normalize_tree() in al_tree_select.py;
   * both sides have to agree about which keys are selectable.
   * ------------------------------------------------------------------ */

  var CHILD_KEYS = ["children", "options", "choices"];

  function childrenOf(item) {
    for (var i = 0; i < CHILD_KEYS.length; i++) {
      if (Object.prototype.hasOwnProperty.call(item, CHILD_KEYS[i])) {
        return item[CHILD_KEYS[i]];
      }
    }
    return null;
  }

  function isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function makeNode(item) {
    if (item === null || item === undefined) {
      return null;
    }
    if (typeof item === "string" || typeof item === "number") {
      return {
        key: String(item),
        label: String(item),
        help: null,
        group: null,
        selectable: true,
        children: [],
      };
    }
    if (Array.isArray(item)) {
      // [label, key] pairs, as docassemble accepts in some places.
      if (item.length === 2) {
        return {
          key: String(item[1]),
          label: String(item[0]),
          help: null,
          group: null,
          selectable: true,
          children: [],
        };
      }
      return null;
    }
    if (!isPlainObject(item)) {
      return null;
    }

    var hasStructure =
      Object.prototype.hasOwnProperty.call(item, "label") ||
      Object.prototype.hasOwnProperty.call(item, "key") ||
      childrenOf(item) !== null;

    if (!hasStructure) {
      var keys = Object.keys(item);
      if (keys.length !== 1) {
        return null;
      }
      var onlyKey = keys[0];
      var onlyValue = item[onlyKey];
      if (Array.isArray(onlyValue)) {
        // `- Housing: [ ... ]` -- a group whose label is the mapping key.
        return {
          key: null,
          label: String(onlyKey),
          help: null,
          group: null,
          selectable: false,
          children: normalizeChoices(onlyValue),
        };
      }
      if (isPlainObject(onlyValue)) {
        var nested = makeNode(onlyValue);
        if (nested && nested.key === null) {
          nested.key = String(onlyKey);
          nested.selectable = nested.children.length === 0;
        }
        return nested;
      }
      // `- HO-01: Eviction` -- the docassemble key/label shorthand.
      return {
        key: String(onlyKey),
        label: String(onlyValue),
        help: null,
        group: null,
        selectable: true,
        children: [],
      };
    }

    var rawChildren = childrenOf(item);
    var children = rawChildren ? normalizeChoices(rawChildren) : [];
    var key =
      item.key === undefined || item.key === null ? null : String(item.key);
    var label =
      item.label === undefined || item.label === null
        ? key === null
          ? ""
          : key
        : String(item.label);
    // A YAML block scalar keeps its trailing newline; nobody means to include it.
    var help = String(item.help || item.description || "").trim() || null;
    var selectable;
    if (Object.prototype.hasOwnProperty.call(item, "selectable")) {
      selectable = Boolean(item.selectable) && key !== null;
    } else {
      // Leaves are selectable. A group is only selectable when it was given an
      // explicit key, which is how a taxonomy says "you may pick the category
      // itself as well as anything under it".
      selectable = key !== null;
    }
    return {
      key: key,
      label: label,
      help: help,
      group: item.group === undefined ? null : item.group,
      selectable: selectable,
      children: children,
    };
  }

  function normalizeChoices(raw) {
    if (raw === null || raw === undefined) {
      return [];
    }
    var items;
    if (Array.isArray(raw)) {
      items = raw;
    } else if (isPlainObject(raw)) {
      var asNode = makeNode(raw);
      if (asNode) {
        return applyGroups([asNode]);
      }
      items = Object.keys(raw).map(function (key) {
        var single = {};
        single[key] = raw[key];
        return single;
      });
    } else {
      items = [raw];
    }
    var nodes = [];
    for (var i = 0; i < items.length; i++) {
      var node = makeNode(items[i]);
      if (node) {
        nodes.push(node);
      }
    }
    return applyGroups(nodes);
  }

  /* Turn a flat list that uses `group:` into a real tree, which is how the
   * older bootstrap-multiselect based hierarchical select expressed nesting. */
  function applyGroups(nodes) {
    var anyGroups = nodes.some(function (node) {
      return (
        node.group !== null && node.group !== undefined && node.group !== ""
      );
    });
    if (!anyGroups) {
      return nodes;
    }
    var out = [];
    var byPath = {};

    function containerFor(path) {
      if (!path.length) {
        return out;
      }
      var joined = path.join("\x00");
      if (byPath[joined]) {
        return byPath[joined].children;
      }
      var parent = containerFor(path.slice(0, -1));
      var group = {
        key: null,
        label: String(path[path.length - 1]),
        help: null,
        group: null,
        selectable: false,
        children: [],
      };
      parent.push(group);
      byPath[joined] = group;
      return group.children;
    }

    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var path = [];
      if (Array.isArray(node.group)) {
        path = node.group.slice();
      } else if (
        node.group !== null &&
        node.group !== undefined &&
        node.group !== ""
      ) {
        path = [node.group];
      }
      node.group = null;
      containerFor(path).push(node);
    }
    return out;
  }

  function countSelectable(nodes) {
    var total = 0;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].selectable) {
        total += 1;
      }
      total += countSelectable(nodes[i].children);
    }
    return total;
  }

  function hasGroups(nodes) {
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].children.length) {
        return true;
      }
    }
    return false;
  }

  /* ------------------------------------------------------------------ *
   * Reading the field's own configuration
   * ------------------------------------------------------------------ */

  function attr($input, name) {
    var value = $input.attr("data-" + name.toLowerCase());
    return value === undefined ? null : value;
  }

  function boolAttr($input, name, fallback) {
    var value = attr($input, name);
    if (value === null || value === "") {
      return fallback;
    }
    return !/^(false|no|none|0|off)$/i.test(String(value).trim());
  }

  function intAttr($input, name) {
    var value = attr($input, name);
    if (value === null || String(value).trim() === "") {
      return null;
    }
    var parsed = parseInt(String(value).trim(), 10);
    return isNaN(parsed) ? null : parsed;
  }

  function parseValue(raw) {
    if (raw === undefined || raw === null) {
      return [];
    }
    var text = String(raw).trim();
    if (text === "") {
      return [];
    }
    var parsed = null;
    try {
      parsed = JSON.parse(text);
    } catch (err) {
      parsed = null;
    }
    if (parsed === null) {
      try {
        parsed = parsePythonLiteral(text);
      } catch (err2) {
        parsed = null;
      }
    }
    if (Array.isArray(parsed)) {
      return parsed.map(String);
    }
    if (isPlainObject(parsed)) {
      // A dict of key -> truthy, i.e. what a DADict looks like.
      return Object.keys(parsed).filter(function (key) {
        return Boolean(parsed[key]);
      });
    }
    if (typeof parsed === "string") {
      return [parsed];
    }
    // Last resort: a bare or comma separated list of keys.
    return text
      .split(",")
      .map(function (part) {
        return part.trim();
      })
      .filter(Boolean);
  }

  /* ------------------------------------------------------------------ *
   * Building the widget
   * ------------------------------------------------------------------ */

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) {
      return;
    }
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.appendChild(document.createTextNode(AL_TREE_CSS));
    document.head.appendChild(style);
  }

  /* docassemble renders the field as
   *   <div class="da-form-group row ... da-field-container-datatype-al_tree_select">
   *     <label for="ID" ...>Label</label>
   *     <div class="... dafieldpart"><input ...></div>
   *   </div>
   * The question text is a label pointing at a single control, but what the
   * user actually operates is a group of checkboxes. Rather than rewrite
   * docassemble's markup into a fieldset -- which would disturb the grid
   * classes that show-if and required styling depend on -- keep the element
   * and re-point it: the group gets role="group" plus aria-labelledby, which
   * ARIA defines as equivalent to fieldset/legend.
   *
   * Returns the id to use in aria-labelledby, or null if there is no label. */
  function labelIdFor($input, idBase) {
    var $container = $input.closest(
      ".da-field-container-datatype-al_tree_select",
    );
    if (!$container.length) {
      $container = $input.closest(".da-form-group");
    }
    var $label = $container.children("label").first();
    if (!$label.length) {
      return null;
    }
    var labelId = $label.attr("id");
    if (!labelId) {
      labelId = idBase + "-label";
      $label.attr("id", labelId);
    }
    // A `for` pointing at a hidden input would send a screen reader user to a
    // control they cannot reach.
    if ($label.attr("for")) {
      $label.attr("data-al-old-for", $label.attr("for"));
      $label.removeAttr("for");
    }
    return labelId;
  }

  function makeSearch(ctx) {
    var $wrapper = $('<div class="al-tree-search mb-2"></div>');
    var searchId = ctx.idBase + "-search";
    var $label = $('<label class="form-label"></label>')
      .attr("for", searchId)
      .text(str(ctx, "searchLabel"));
    var $field = $(
      '<input type="search" class="form-control danovalidation" autocomplete="off">',
    )
      .attr("id", searchId)
      .attr("placeholder", str(ctx, "searchPlaceholder"))
      .attr("aria-describedby", ctx.idBase + "-status");
    $wrapper.append($label).append($field);
    ctx.$search = $field;

    var timer = null;
    $field.on("input", function () {
      var value = $field.val();
      applyFilter(ctx, value);
      // Announce after typing settles so a screen reader is not interrupted on
      // every keystroke.
      if (timer) {
        clearTimeout(timer);
      }
      timer = setTimeout(function () {
        announceFilter(ctx, value);
      }, 500);
    });
    $field.on("keydown", function (event) {
      if (event.key === "Enter") {
        // Enter in a lone text field submits the form. Someone narrowing a
        // list is not trying to answer the question yet.
        event.preventDefault();
        announceFilter(ctx, $field.val());
      } else if (event.key === "Escape" && $field.val() !== "") {
        event.stopPropagation();
        $field.val("");
        applyFilter(ctx, "");
        announceFilter(ctx, "");
      }
    });
    return $wrapper;
  }

  function makeToolbar(ctx) {
    var $wrapper = $('<div class="al-tree-toolbar mb-2"></div>');
    if (ctx.hasGroups) {
      var $expand = $(
        '<button type="button" class="btn btn-sm btn-outline-secondary"></button>',
      )
        .text(str(ctx, "expandAll"))
        .on("click", function () {
          setAllOpen(ctx, true);
        });
      var $collapse = $(
        '<button type="button" class="btn btn-sm btn-outline-secondary"></button>',
      )
        .text(str(ctx, "collapseAll"))
        .on("click", function () {
          setAllOpen(ctx, false);
        });
      $wrapper.append($expand).append($collapse);
    }
    var $clear = $(
      '<button type="button" class="btn btn-sm btn-outline-secondary"></button>',
    )
      .text(str(ctx, "clearAll"))
      .on("click", function () {
        ctx.leaves.forEach(function (leaf) {
          leaf.$input.prop("checked", false);
        });
        syncFromCheckboxes(ctx, true);
      });
    $wrapper.append($clear);
    ctx.$toolbar = $wrapper;
    return $wrapper;
  }

  function renderNodes(ctx, nodes, $container, depth) {
    var rendered = [];
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      if (node.children.length) {
        rendered.push(renderGroup(ctx, node, $container, depth));
      } else if (node.selectable) {
        rendered.push(renderLeaf(ctx, node, $container));
      } else if (node.label) {
        // A node with neither children nor a key is just a heading.
        var $heading = $(
          '<div class="al-tree-heading fw-semibold mt-2"></div>',
        ).text(node.label);
        $container.append($heading);
      }
    }
    return rendered;
  }

  function renderLeaf(ctx, node, $container) {
    idCounter += 1;
    var inputId = ctx.idBase + "-opt-" + idCounter;
    var $wrapper = $('<div class="form-check al-tree-item"></div>');
    var $input = $(
      '<input class="form-check-input danovalidation" type="checkbox">',
    )
      .attr("id", inputId)
      .attr("value", node.key);
    var $label = $('<label class="form-check-label"></label>').attr(
      "for",
      inputId,
    );
    var $labelText = $('<span class="al-tree-item-label"></span>').text(
      node.label,
    );
    $label.append($labelText);
    if (ctx.showKeys && node.key !== node.label) {
      $label.append(document.createTextNode(" "));
      $label.append(
        $('<span class="al-tree-item-key"></span>').text("(" + node.key + ")"),
      );
    }
    $wrapper.append($input).append($label);
    if (node.help) {
      var helpId = inputId + "-help";
      $wrapper.append(
        $('<div class="form-text al-tree-item-help"></div>')
          .attr("id", helpId)
          .text(node.help),
      );
      $input.attr("aria-describedby", helpId);
    }
    $container.append($wrapper);

    var leaf = {
      type: "leaf",
      node: node,
      key: node.key,
      $el: $wrapper,
      $input: $input,
      $labelText: $labelText,
      searchText: (
        node.label +
        " " +
        node.key +
        " " +
        (node.help || "")
      ).toLowerCase(),
    };
    ctx.leaves.push(leaf);
    ctx.leavesByKey[node.key] = leaf;

    $input.on("change", function () {
      syncFromCheckboxes(ctx, true);
    });
    return leaf;
  }

  function renderGroup(ctx, node, $container, depth) {
    var $details = $('<details class="al-tree-group"></details>');
    var $summary = $('<summary class="al-tree-summary"></summary>');
    $summary.append('<span class="al-tree-chevron" aria-hidden="true"></span>');
    var $summaryLabel = $('<span class="al-tree-summary-label"></span>').text(
      node.label,
    );
    $summary.append($summaryLabel);
    var $count = $(
      '<span class="badge text-bg-primary al-tree-count"></span>',
    ).attr("hidden", "hidden");
    $summary.append($count);
    // docassemble listens for Enter on the document and treats it as "submit
    // the form" for anything that is not an input, textarea, link, label or
    // button. A <summary> is none of those, so without this the keyboard way
    // of opening a group would submit the question instead. Stopping the event
    // here leaves the browser's own toggle behavior intact.
    $summary.on("keydown", function (event) {
      if (event.key === "Enter" || event.which === 13) {
        event.stopPropagation();
      }
    });
    $details.append($summary);

    var $children = $('<div class="al-tree-children"></div>');
    $details.append($children);
    $container.append($details);

    var group = {
      type: "group",
      node: node,
      $el: $details,
      $summary: $summary,
      $summaryLabel: $summaryLabel,
      $children: $children,
      $count: $count,
      $selectAll: null,
      children: [],
      searchText: node.label.toLowerCase(),
    };
    ctx.groups.push(group);

    // A group can carry its own key, meaning the category itself is a valid
    // answer alongside anything nested under it. It reads first, before any
    // "select all", because it is the broadest single answer in the group.
    if (node.selectable) {
      var ownLeafNode = {
        key: node.key,
        label: node.label,
        help: node.help,
        selectable: true,
        children: [],
      };
      group.children.push(renderLeaf(ctx, ownLeafNode, $children));
    }

    if (ctx.selectAll) {
      idCounter += 1;
      var allId = ctx.idBase + "-all-" + idCounter;
      var $allWrapper = $('<div class="form-check al-tree-select-all"></div>');
      var $allInput = $(
        '<input class="form-check-input danovalidation" type="checkbox">',
      ).attr("id", allId);
      var $allLabel = $('<label class="form-check-label fst-italic"></label>')
        .attr("for", allId)
        .text(str(ctx, "selectAllLabel", node.label));
      $allWrapper.append($allInput).append($allLabel);
      $children.append($allWrapper);
      group.$selectAll = $allInput;
      group.$selectAllWrapper = $allWrapper;
      $allInput.on("change", function () {
        var checked = $allInput.prop("checked");
        descendantLeaves(group).forEach(function (leaf) {
          if (!leaf.$el.hasClass("al-tree-hidden")) {
            leaf.$input.prop("checked", checked);
          }
        });
        syncFromCheckboxes(ctx, true);
      });
    }

    group.children = group.children.concat(
      renderNodes(ctx, node.children, $children, depth + 1),
    );

    if (ctx.expandDepth === null || depth < ctx.expandDepth) {
      $details.attr("open", "open");
    }
    return group;
  }

  function descendantLeaves(group) {
    var out = [];
    group.children.forEach(function (child) {
      if (child.type === "leaf") {
        out.push(child);
      } else {
        out = out.concat(descendantLeaves(child));
      }
    });
    return out;
  }

  function setAllOpen(ctx, open) {
    ctx.groups.forEach(function (group) {
      group.$el.prop("open", open);
    });
  }

  /* ------------------------------------------------------------------ *
   * Selection state
   * ------------------------------------------------------------------ */

  function selectedKeys(ctx) {
    var seen = {};
    var keys = [];
    ctx.leaves.forEach(function (leaf) {
      if (leaf.$input.prop("checked") && !seen[leaf.key]) {
        seen[leaf.key] = true;
        keys.push(leaf.key);
      }
    });
    return keys;
  }

  function syncFromCheckboxes(ctx, fromUser) {
    var keys = selectedKeys(ctx);
    // An empty selection posts an empty string so that docassemble's own
    // `required` validation behaves exactly as it does for any other field.
    ctx.$input.val(keys.length ? JSON.stringify(keys) : "");
    updateCounts(ctx);
    updateSelectedSummary(ctx);
    if (fromUser) {
      ctx.$input.trigger("change");
      if (ctx.$input.closest("form").data("validator")) {
        ctx.$input.valid();
      }
    }
  }

  function updateCounts(ctx) {
    ctx.groups.forEach(function (group) {
      var leaves = descendantLeaves(group);
      var checked = leaves.filter(function (leaf) {
        return leaf.$input.prop("checked");
      });
      if (checked.length) {
        group.$count.text(String(checked.length)).removeAttr("hidden");
        group.$count.attr(
          "title",
          str(ctx, "groupSelectedCount", checked.length),
        );
      } else {
        group.$count.text("").attr("hidden", "hidden").removeAttr("title");
      }
      if (group.$selectAll) {
        var all = checked.length > 0 && checked.length === leaves.length;
        group.$selectAll.prop("checked", all);
        group.$selectAll.prop(
          "indeterminate",
          checked.length > 0 && checked.length < leaves.length,
        );
      }
    });
  }

  function updateSelectedSummary(ctx) {
    if (!ctx.$selected) {
      return;
    }
    var chosen = ctx.leaves.filter(function (leaf) {
      return leaf.$input.prop("checked");
    });
    ctx.$selectedList.empty();
    if (!chosen.length) {
      ctx.$selectedCount.text(str(ctx, "nothingSelected"));
      return;
    }
    ctx.$selectedCount.text(str(ctx, "selectedCount", chosen.length));
    chosen.forEach(function (leaf) {
      var $chip = $('<button type="button" class="al-tree-chip"></button>')
        .attr("aria-label", str(ctx, "removeSelection", leaf.node.label))
        .on("click", function () {
          leaf.$input.prop("checked", false);
          syncFromCheckboxes(ctx, true);
          leaf.$input.trigger("focus");
        });
      $chip.append($("<span></span>").text(leaf.node.label));
      $chip.append(
        '<span class="al-tree-chip-x" aria-hidden="true">&times;</span>',
      );
      ctx.$selectedList.append($chip);
    });
  }

  /* ------------------------------------------------------------------ *
   * Filtering
   * ------------------------------------------------------------------ */

  function applyFilter(ctx, rawQuery) {
    var query = String(rawQuery || "")
      .toLowerCase()
      .trim();
    ctx.matchCount = 0;

    function walk(items, ancestorMatched) {
      var anyVisible = false;
      items.forEach(function (item) {
        if (item.type === "leaf") {
          var matched =
            query === "" ||
            ancestorMatched ||
            item.searchText.indexOf(query) !== -1;
          // Never hide something the user has already chosen; losing sight of
          // a selection while filtering is disorienting.
          var visible = matched || item.$input.prop("checked");
          item.$el.toggleClass("al-tree-hidden", !visible);
          if (matched && query !== "") {
            ctx.matchCount += 1;
          }
          highlight(
            item.$labelText,
            item.node.label,
            query && !ancestorMatched ? query : "",
          );
          anyVisible = anyVisible || visible;
        } else {
          var groupMatched =
            ancestorMatched ||
            (query !== "" && item.searchText.indexOf(query) !== -1);
          var childVisible = walk(item.children, groupMatched);
          var showGroup = query === "" || groupMatched || childVisible;
          item.$el.toggleClass("al-tree-hidden", !showGroup);
          if (item.$selectAllWrapper) {
            item.$selectAllWrapper.toggleClass("al-tree-hidden", query !== "");
          }
          if (query !== "" && showGroup) {
            item.$el.prop("open", true);
          } else if (query === "") {
            item.$el.prop(
              "open",
              item.wasOpen === undefined ? item.$el.prop("open") : item.wasOpen,
            );
          }
          highlight(item.$summaryLabel, item.node.label, query);
          anyVisible = anyVisible || showGroup;
        }
      });
      return anyVisible;
    }

    if (query !== "" && !ctx.filtering) {
      // Remember how the tree looked so clearing the filter restores it.
      ctx.groups.forEach(function (group) {
        group.wasOpen = group.$el.prop("open");
      });
      ctx.filtering = true;
    } else if (query === "") {
      ctx.filtering = false;
    }

    walk(ctx.rendered, false);
    ctx.$noResults.toggleClass(
      "al-tree-hidden",
      !(query !== "" && ctx.matchCount === 0),
    );
  }

  function highlight($target, text, query) {
    if (!query) {
      $target.text(text);
      return;
    }
    var index = text.toLowerCase().indexOf(query);
    if (index === -1) {
      $target.text(text);
      return;
    }
    $target.empty();
    $target.append(document.createTextNode(text.slice(0, index)));
    $target.append(
      $("<mark class='al-tree-match'></mark>").text(
        text.slice(index, index + query.length),
      ),
    );
    $target.append(document.createTextNode(text.slice(index + query.length)));
  }

  function announceFilter(ctx, rawQuery) {
    var query = String(rawQuery || "").trim();
    if (query === "") {
      ctx.$status.text(str(ctx, "filterCleared", ctx.totalOptions));
    } else if (ctx.matchCount === 0) {
      ctx.$status.text(str(ctx, "noResults"));
    } else {
      ctx.$status.text(
        str(ctx, "resultsFound", ctx.matchCount, ctx.totalOptions),
      );
    }
  }

  /* ------------------------------------------------------------------ *
   * Validation of the minimum/maximum number of selections
   * ------------------------------------------------------------------ */

  function addValidationRules(ctx) {
    if (!$.validator || !ctx.$input.closest("form").length) {
      return;
    }

    // The backing input contains JSON, so docassemble's generic field rules
    // do not apply: `required` is controlled by whether alMinlength is
    // present, and the prefixed limits count selected keys rather than
    // characters.
    try {
      ctx.$input.rules("remove", "required minlength maxlength");
    } catch (err) {
      // The form has no validator yet; the server-side check still applies.
    }
    if (ctx.min === null && ctx.max === null) {
      return;
    }
    var rules = {};
    var messages = {};
    if (ctx.min !== null) {
      rules.alTreeSelectMin = ctx.min;
      messages.alTreeSelectMin = str(ctx, "minMessage", ctx.min);
    }
    if (ctx.max !== null) {
      rules.alTreeSelectMax = ctx.max;
      messages.alTreeSelectMax = str(ctx, "maxMessage", ctx.max);
    }
    rules.messages = messages;
    try {
      ctx.$input.rules("add", rules);
    } catch (err) {
      // The form has no validator yet; the server-side check still applies.
    }
  }

  function countFromValue(value) {
    return parseValue(value).length;
  }

  if (window.$ && $.validator) {
    if (!$.validator.methods.alTreeSelectMin) {
      $.validator.addMethod(
        "alTreeSelectMin",
        function (value, element, param) {
          var count = countFromValue(value);
          return count >= param;
        },
      );
    }
    if (!$.validator.methods.alTreeSelectMax) {
      $.validator.addMethod(
        "alTreeSelectMax",
        function (value, element, param) {
          return countFromValue(value) <= param;
        },
      );
    }
  }

  /* ------------------------------------------------------------------ *
   * Setup
   * ------------------------------------------------------------------ */

  function setUp(input) {
    var $input = $(input);
    injectStyles();

    var raw = attr($input, "choices");
    if (raw === null) {
      raw = attr($input, "code");
    }
    var choices;
    try {
      choices = normalizeChoices(parseChoiceData(raw));
    } catch (err) {
      console.error(
        "al_tree_select: could not read the choices for this field.",
        err,
      );
      choices = [];
    }
    if (!choices.length) {
      console.error(
        "al_tree_select: no choices were found. Give the field a `choices:` or `code:` specifier.",
      );
    }

    idCounter += 1;
    var ctx = {
      $input: $input,
      idBase: "al-tree-" + idCounter,
      strings: {},
      leaves: [],
      leavesByKey: {},
      groups: [],
      matchCount: 0,
      filtering: false,
    };

    Object.keys(DEFAULT_STRINGS).forEach(function (name) {
      var value = attr(
        $input,
        "al" + name.charAt(0).toUpperCase() + name.slice(1),
      );
      if (value !== null && value !== "") {
        ctx.strings[name] = value;
      }
    });

    ctx.totalOptions = countSelectable(choices);
    ctx.hasGroups = hasGroups(choices);
    ctx.showKeys = boolAttr($input, "alShowKeys", false);
    ctx.selectAll = boolAttr($input, "alSelectAll", false) && ctx.hasGroups;
    ctx.min = intAttr($input, "alMinlength");
    ctx.max = intAttr($input, "alMaxlength");
    // An al_tree_select is optional unless alMinlength is supplied. The hidden
    // backing input may otherwise inherit docassemble's default `required`
    // attribute even though the visible controls are checkboxes.
    $input.removeAttr("required").prop("required", false);

    var expandRaw = attr($input, "alExpand");
    if (expandRaw === null || expandRaw === "") {
      // Collapsed by default once the tree is big enough that an expanded view
      // would be a wall of checkboxes. `alExpand` overrides this, either as a
      // yes/no or as the number of levels to open.
      ctx.expandDepth = ctx.totalOptions <= 12 ? null : 0;
    } else if (/^\d+$/.test(String(expandRaw).trim())) {
      ctx.expandDepth = parseInt(String(expandRaw).trim(), 10);
    } else {
      ctx.expandDepth = boolAttr($input, "alExpand", true) ? null : 0;
    }

    var showSearch = boolAttr($input, "alSearch", ctx.totalOptions > 10);
    var showToolbar = boolAttr(
      $input,
      "alToolbar",
      ctx.hasGroups || ctx.totalOptions > 10,
    );
    var showSelected = boolAttr($input, "alShowSelected", true);

    var $widget = $('<div class="al-tree-select"></div>').attr(
      "id",
      ctx.idBase,
    );
    var maxHeight = attr($input, "alMaxHeight");
    if (maxHeight) {
      $widget.css("--al-tree-max-height", maxHeight);
    }

    var $status = $(
      '<div class="al-tree-sr-only" role="status" aria-live="polite" aria-atomic="true"></div>',
    ).attr("id", ctx.idBase + "-status");
    ctx.$status = $status;

    if (showSearch) {
      $widget.append(makeSearch(ctx));
    }
    if (showToolbar) {
      $widget.append(makeToolbar(ctx));
    }
    $widget.append($status);

    var $body = $('<div class="al-tree-body" role="group"></div>');
    var labelId = labelIdFor($input, ctx.idBase);
    if (labelId) {
      $body.attr("aria-labelledby", labelId);
    }
    // jQuery Validation names its message span after the input, so pointing at
    // it now means the message is announced with the group once it appears.
    if ($input.attr("id")) {
      $body.attr("aria-describedby", $input.attr("id") + "-error");
    }
    $widget.append($body);
    ctx.$body = $body;

    ctx.rendered = renderNodes(ctx, choices, $body, 0);

    ctx.$noResults = $(
      '<div class="al-tree-no-results al-tree-hidden"></div>',
    ).text(str(ctx, "noResults"));
    $body.append(ctx.$noResults);

    if (showSelected) {
      var $selected = $('<div class="al-tree-selected"></div>');
      ctx.$selectedCount = $('<div class="small fw-semibold"></div>');
      ctx.$selectedList = $('<div class="al-tree-chips"></div>');
      $selected.append(ctx.$selectedCount).append(ctx.$selectedList);
      $widget.append($selected);
      ctx.$selected = $selected;
    }

    $input.after($widget);

    if ($input.prop("disabled")) {
      $widget.find("input").prop("disabled", true);
      $widget.find("button").prop("disabled", true);
    }

    // Restore any value already on the field: a previously answered question,
    // a `default:`, or the value the user posted before a validation error.
    parseValue($input.val()).forEach(function (key) {
      var leaf = ctx.leavesByKey[key];
      if (leaf) {
        leaf.$input.prop("checked", true);
        leaf.$el.parents("details.al-tree-group").prop("open", true);
      }
    });

    syncFromCheckboxes(ctx, false);
    addValidationRules(ctx);
    $input.data("alTreeSelectContext", ctx);
  }

  function init() {
    $("input.al_tree_select").each(function () {
      if ($(this).data("alTreeSelectReady")) {
        return;
      }
      $(this).data("alTreeSelectReady", true);
      try {
        setUp(this);
      } catch (err) {
        console.error("al_tree_select: failed to set up the field.", err);
      }
    });
  }

  $(document).on("daPageLoad", init);
  $(init);
})();
