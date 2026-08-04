"""An accessible, translatable, Bootstrap-native hierarchical selection input.

`datatype: al_tree_select` renders a set of nested `<details>`/`<summary>`
disclosure groups containing ordinary checkboxes, and stores the answer in a
`DADict` -- exactly what `datatype: checkboxes` gives you.

    ---
    question: |
      What kinds of problems are you having?
    fields:
      - Legal issues: legal_issues
        datatype: al_tree_select
        choices:
          - label: Housing
            children:
              - label: Eviction
                key: HO-01
              - label: Bad conditions
                key: HO-02
          - label: Family
            children:
              - label: Divorce
                key: FA-01
    ---

`legal_issues` is then a `DADict` whose keys are every selectable key in the
tree, so `legal_issues["HO-01"]`, `legal_issues.true_values()` and
`legal_issues.any_true()` all work the way they do for checkboxes.

This is an alternative to the older `bootstrap-multiselect` based hierarchical
multi-select in `multiselect.yml`, which is still available. Unlike that one,
this input needs no `include:`, no `script:` block and no base64 encoded ids,
uses only native form controls, and works with a keyboard, a screen reader and
browser find-in-page.
"""

import ast
import json
import os
from typing import Any, Dict, List, Optional, Union

from docassemble.base.util import (
    CustomDataType,
    DADict,
    DAValidationError,
    log,
    word,
)

__all__ = ["ALTreeSelect", "normalize_tree", "tree_keys"]


# ---------------------------------------------------------------------------
# Reading the `choices:` / `code:` specifier
# ---------------------------------------------------------------------------

# Keys that may hold the children of a node, so that a developer who is used to
# `options:` or a nested `choices:` does not have to look anything up.
_CHILD_KEYS = ("children", "options", "choices")


def _load(raw: Any) -> Any:
    """Return `raw` as a Python data structure.

    A `choices:` block reaches us as the parsed YAML, so usually there is
    nothing to do. A string is accepted too, since it is convenient to build the
    tree elsewhere and hand over JSON.
    """
    if not isinstance(raw, str):
        return raw
    text = raw.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        pass
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None


def _children_of(item: Dict[str, Any]) -> Optional[Any]:
    for name in _CHILD_KEYS:
        if name in item:
            return item[name]
    return None


def _make_node(item: Any) -> Optional[Dict[str, Any]]:
    """Turn one entry of a `choices:` list into a normalized node."""
    if item is None:
        return None

    if isinstance(item, (str, int, float)) and not isinstance(item, bool):
        return {
            "key": str(item),
            "label": str(item),
            "help": None,
            "group": None,
            "selectable": True,
            "children": [],
        }

    if isinstance(item, (list, tuple)):
        # A (label, key) pair, which docassemble accepts in a few places.
        if len(item) == 2:
            return {
                "key": str(item[1]),
                "label": str(item[0]),
                "help": None,
                "group": None,
                "selectable": True,
                "children": [],
            }
        return None

    if not isinstance(item, dict):
        return None

    has_structure = "label" in item or "key" in item or _children_of(item) is not None

    if not has_structure:
        if len(item) != 1:
            return None
        only_key = list(item.keys())[0]
        only_value = item[only_key]
        if isinstance(only_value, (list, tuple)):
            # `- Housing: [ ... ]`, a group labeled with the mapping key.
            return {
                "key": None,
                "label": str(only_key),
                "help": None,
                "group": None,
                "selectable": False,
                "children": normalize_tree(only_value),
            }
        if isinstance(only_value, dict):
            nested = _make_node(only_value)
            if nested is not None and nested["key"] is None:
                nested["key"] = str(only_key)
                nested["selectable"] = not nested["children"]
            return nested
        # `- HO-01: Eviction`, the docassemble key/label shorthand.
        return {
            "key": str(only_key),
            "label": str(only_value),
            "help": None,
            "group": None,
            "selectable": True,
            "children": [],
        }

    raw_children = _children_of(item)
    children = normalize_tree(raw_children) if raw_children else []
    key = None if item.get("key") is None else str(item["key"])
    if item.get("label") is None:
        label = "" if key is None else key
    else:
        label = str(item["label"])
    # A YAML block scalar keeps its trailing newline; nobody means to include it.
    help_text = str(item.get("help", item.get("description")) or "").strip() or None
    if "selectable" in item:
        selectable = bool(item["selectable"]) and key is not None
    else:
        # Leaves are selectable. A group counts as selectable only when it was
        # given an explicit key, which is how a taxonomy says "the category
        # itself is a valid answer as well as anything under it".
        selectable = key is not None
    return {
        "key": key,
        "label": label,
        "help": help_text,
        "group": item.get("group"),
        "selectable": selectable,
        "children": children,
    }


def _apply_groups(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Nest a flat list that uses `group:`.

    This is how the `bootstrap-multiselect` based hierarchical select expressed
    nesting, so a flat list of choices can be moved over unchanged. A `group:`
    may be a single name or a list of names for deeper nesting.
    """
    if not any(node.get("group") for node in nodes):
        return nodes

    out: List[Dict[str, Any]] = []
    by_path: Dict[str, Dict[str, Any]] = {}

    def container_for(path: List[str]) -> List[Dict[str, Any]]:
        if not path:
            return out
        joined = "\x00".join(path)
        if joined in by_path:
            return by_path[joined]["children"]
        parent = container_for(path[:-1])
        children: List[Dict[str, Any]] = []
        group: Dict[str, Any] = {
            "key": None,
            "label": str(path[-1]),
            "help": None,
            "group": None,
            "selectable": False,
            "children": children,
        }
        parent.append(group)
        by_path[joined] = group
        return children

    for node in nodes:
        raw_group = node.get("group")
        if isinstance(raw_group, (list, tuple)):
            path = [str(part) for part in raw_group]
        elif raw_group:
            path = [str(raw_group)]
        else:
            path = []
        node["group"] = None
        container_for(path).append(node)
    return out


def normalize_tree(raw: Any) -> List[Dict[str, Any]]:
    """Turn anything a developer may write under `choices:` into a list of nodes.

    Every node is a dict with `key`, `label`, `help`, `selectable` and
    `children`. Kept in step with `normalizeChoices()` in `al_tree_select.js`;
    both sides have to agree about which keys are selectable.
    """
    raw = _load(raw)
    if raw is None:
        return []

    if isinstance(raw, dict):
        as_node = _make_node(raw)
        if as_node is not None:
            return _apply_groups([as_node])
        items: List[Any] = [{key: value} for key, value in raw.items()]
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        items = [raw]

    nodes = []
    for item in items:
        node = _make_node(item)
        if node is not None:
            nodes.append(node)
    return _apply_groups(nodes)


def tree_keys(nodes: List[Dict[str, Any]]) -> List[str]:
    """Every selectable key in the tree, in the order it is displayed."""
    keys: List[str] = []

    def walk(items: List[Dict[str, Any]]) -> None:
        for node in items:
            # A selectable group is rendered as a checkbox above its children,
            # so its key comes first.
            if node["selectable"] and node["key"] is not None:
                keys.append(node["key"])
            walk(node["children"])

    walk(nodes)
    seen = set()
    unique = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def _selected_from(item: Any) -> List[str]:
    """Read a posted value, a DADict, a dict or a list as a list of keys."""
    if item is None:
        return []
    if isinstance(item, DADict) or (
        hasattr(item, "elements") and isinstance(getattr(item, "elements"), dict)
    ):
        return [str(key) for key, value in item.elements.items() if value]
    if isinstance(item, dict):
        return [str(key) for key, value in item.items() if value]
    if isinstance(item, (list, tuple, set)):
        return [str(entry) for entry in item]
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return []
        loaded = _load(text)
        if isinstance(loaded, (list, tuple, set)):
            return [str(entry) for entry in loaded]
        if isinstance(loaded, dict):
            return [str(key) for key, value in loaded.items() if value]
        # A bare key, or a comma separated list of them.
        return [part.strip() for part in text.split(",") if part.strip()]
    return [str(item)]


def _choices_from_field_data(data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not data:
        return []
    for name in ("choices", "code"):
        if data.get(name) is not None:
            try:
                return normalize_tree(data[name])
            except Exception as error:
                log(f"al_tree_select: could not read `{name}`: {error}")
                return []
    return []


def _int_or_none(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# The JavaScript, which lives next to the CSS in data/static so that both stay
# lintable and readable.
# ---------------------------------------------------------------------------


def _read_asset(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "data", "static", filename)
    with open(path, "r", encoding="utf-8") as asset:
        return asset.read()


def _build_javascript() -> str:
    javascript = _read_asset("al_tree_select.js")
    css = _read_asset("al_tree_select.css")
    # The stylesheet is injected by the script, so `datatype: al_tree_select` is
    # all a developer needs; there is no CSS file to remember to include.
    return javascript.replace('"__AL_TREE_SELECT_CSS__"', json.dumps(css))


try:
    js_text = _build_javascript()
except Exception as _error:  # pragma: no cover - only if packaging goes wrong
    log(f"al_tree_select: could not load its JavaScript: {_error}")
    js_text = ""


class ALTreeSelect(CustomDataType):
    """A hierarchical, searchable set of checkboxes that saves to a `DADict`."""

    name = "al_tree_select"
    # The real control is the tree the JavaScript builds; this input only
    # carries the value. Rendering it hidden from the start avoids a flash of
    # an empty text box before the widget appears. docassemble validates hidden
    # inputs, so `required:` and the min/max rules still apply.
    input_type = "hidden"
    input_class = "al_tree_select"
    javascript = js_text
    # `transform` returns a real DADict rather than a string.
    is_object = True

    # The tree itself. `choices:` is the literal YAML; `code:` is a Python
    # expression, which is also what `choices: {code: ...}` turns into. Use
    # `code:` when the labels need `word()` for translation.
    parameters = ["choices"]
    code_parameters = ["code"]

    # Everything the widget says for itself, so an interview can translate it
    # with `${ word("...") }`. `%d` and `%s` are filled in by the widget.
    mako_parameters = [
        "alSearchLabel",
        "alSearchPlaceholder",
        "alExpandAll",
        "alCollapseAll",
        "alClearAll",
        "alSelectAllLabel",
        "alNoResults",
        "alResultsFound",
        "alFilterCleared",
        "alSelectedCount",
        "alNothingSelected",
        "alRemoveSelection",
        "alGroupSelectedCount",
        "alMinMessage",
        "alMaxMessage",
        # Appearance and behavior.
        "alSearch",
        "alToolbar",
        "alExpand",
        "alSelectAll",
        "alShowKeys",
        "alShowSelected",
        "alMaxHeight",
    ]

    @classmethod
    def validate(cls, item: Any, variable_name: str, data: Dict[str, Any]) -> bool:  # type: ignore[override]
        """Check that the posted keys exist in the tree and honor `min`/`max`."""
        selected = _selected_from(item)
        choices = _choices_from_field_data(data)
        if choices:
            allowed = set(tree_keys(choices))
            unknown = [key for key in selected if key not in allowed]
            if unknown:
                raise DAValidationError(
                    word("Your answer includes a choice that is not on the list.")
                )
        minimum = _int_or_none((data or {}).get("min"))
        maximum = _int_or_none((data or {}).get("max"))
        # An empty answer means "nothing selected"; `required:` is what makes an
        # answer mandatory, exactly as it does for checkboxes.
        if minimum is not None and selected and len(selected) < minimum:
            raise DAValidationError(
                word("Please choose at least {num}.").format(num=minimum)
            )
        if maximum is not None and len(selected) > maximum:
            raise DAValidationError(
                word("Please choose no more than {num}.").format(num=maximum)
            )
        return True

    @classmethod
    def transform(cls, item: Any, variable_name: str, data: Dict[str, Any]) -> DADict:  # type: ignore[override]
        """Build the `DADict` the interview will see.

        Every selectable key in the tree gets an entry, so code can ask about a
        choice the user did not pick without a `KeyError` -- the same contract
        as `datatype: checkboxes`.
        """
        selected = _selected_from(item)
        choices = _choices_from_field_data(data)
        result = DADict(variable_name, auto_gather=False, gathered=True)
        keys = tree_keys(choices)
        if not keys:
            # No choices reached us (an unusual code path, or a misconfigured
            # field). Keep what the user picked rather than losing it.
            keys = list(dict.fromkeys(selected))
        chosen = set(selected)
        for key in keys:
            result[key] = key in chosen
        return result

    @classmethod
    def default_for(  # type: ignore[override]
        cls, item: Any, variable_name: str, data: Dict[str, Any]
    ) -> Optional[str]:
        """Put an existing answer back into the input so it can be re-shown."""
        selected = _selected_from(item)
        if not selected:
            return ""
        return json.dumps(selected)
