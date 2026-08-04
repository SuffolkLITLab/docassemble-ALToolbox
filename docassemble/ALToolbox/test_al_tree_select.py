# do not pre-load

import unittest

from .al_tree_select import (
    ALTreeSelect,
    _load,
    _selected_from,
    normalize_tree,
    tree_keys,
)

_thread_context = None


def setUpModule() -> None:
    """Give DADict somewhere to look up its gathering mode.

    Outside a request, docassemble's `this_thread` resolves to None, and any
    DADict method that could trigger gathering (`keys()`, `true_values()`)
    blows up on it. Newer docassemble exposes a context manager for exactly
    this; on older versions `this_thread` is an ordinary thread local that is
    already usable.
    """
    global _thread_context
    try:
        from docassemble.base.thread_context import empty_globals, global_context
    except ImportError:
        return
    _thread_context = global_context(empty_globals())
    _thread_context.__enter__()


def tearDownModule() -> None:
    if _thread_context is not None:
        _thread_context.__exit__(None, None, None)


class TestNormalizeTree(unittest.TestCase):
    def test_nested_children(self) -> None:
        nodes = normalize_tree(
            [
                {
                    "label": "Housing",
                    "children": [
                        {"label": "Eviction", "key": "HO-01"},
                        {"label": "Repairs", "key": "HO-02"},
                    ],
                }
            ]
        )
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["label"], "Housing")
        # A group without its own key is not something the user can choose.
        self.assertFalse(nodes[0]["selectable"])
        self.assertEqual(tree_keys(nodes), ["HO-01", "HO-02"])

    def test_group_with_its_own_key_is_selectable(self) -> None:
        nodes = normalize_tree(
            [
                {
                    "label": "Housing",
                    "key": "HO",
                    "children": [{"label": "Eviction", "key": "HO-01"}],
                }
            ]
        )
        self.assertTrue(nodes[0]["selectable"])
        # The group's own key is rendered above its children, so it comes first.
        self.assertEqual(tree_keys(nodes), ["HO", "HO-01"])

    def test_selectable_false_wins(self) -> None:
        nodes = normalize_tree([{"label": "Housing", "key": "HO", "selectable": False}])
        self.assertFalse(nodes[0]["selectable"])
        self.assertEqual(tree_keys(nodes), [])

    def test_plain_strings(self) -> None:
        nodes = normalize_tree(["apple", "pear"])
        self.assertEqual(tree_keys(nodes), ["apple", "pear"])
        self.assertEqual(nodes[0]["label"], "apple")

    def test_key_label_shorthand(self) -> None:
        nodes = normalize_tree([{"HO-01": "Eviction"}, {"HO-02": "Repairs"}])
        self.assertEqual(tree_keys(nodes), ["HO-01", "HO-02"])
        self.assertEqual(nodes[0]["label"], "Eviction")

    def test_mapping_shorthand_for_groups(self) -> None:
        nodes = normalize_tree(
            [{"Housing": [{"HO-01": "Eviction"}, {"HO-02": "Repairs"}]}]
        )
        self.assertEqual(nodes[0]["label"], "Housing")
        self.assertFalse(nodes[0]["selectable"])
        self.assertEqual(tree_keys(nodes), ["HO-01", "HO-02"])

    def test_options_and_choices_are_accepted_as_children(self) -> None:
        for child_key in ("children", "options", "choices"):
            nodes = normalize_tree(
                [{"label": "Housing", child_key: [{"label": "Eviction", "key": "HO"}]}]
            )
            self.assertEqual(tree_keys(nodes), ["HO"], child_key)

    def test_flat_list_with_group(self) -> None:
        nodes = normalize_tree(
            [
                {"label": "BMC", "key": "bmc", "group": "Massachusetts"},
                {"label": "Probate", "key": "probate", "group": "Massachusetts"},
                {"label": "Superior", "key": "superior", "group": "Rhode Island"},
            ]
        )
        self.assertEqual(
            [node["label"] for node in nodes], ["Massachusetts", "Rhode Island"]
        )
        self.assertEqual(len(nodes[0]["children"]), 2)
        self.assertEqual(tree_keys(nodes), ["bmc", "probate", "superior"])

    def test_nested_group_paths(self) -> None:
        nodes = normalize_tree(
            [
                {"label": "Eviction", "key": "HO-01", "group": ["Housing", "Tenancy"]},
                {"label": "Repairs", "key": "HO-02", "group": ["Housing", "Tenancy"]},
                {"label": "Zoning", "key": "HO-03", "group": ["Housing"]},
            ]
        )
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["label"], "Housing")
        self.assertEqual(nodes[0]["children"][0]["label"], "Tenancy")
        self.assertEqual(tree_keys(nodes), ["HO-01", "HO-02", "HO-03"])

    def test_help_text(self) -> None:
        nodes = normalize_tree([{"label": "Eviction", "key": "HO", "help": "Explain"}])
        self.assertEqual(nodes[0]["help"], "Explain")

    def test_duplicate_keys_appear_once(self) -> None:
        nodes = normalize_tree(
            [
                {"label": "Housing", "children": [{"label": "Eviction", "key": "HO"}]},
                {"label": "Renting", "children": [{"label": "Eviction", "key": "HO"}]},
            ]
        )
        self.assertEqual(tree_keys(nodes), ["HO"])

    def test_empty_and_garbage_input(self) -> None:
        self.assertEqual(normalize_tree(None), [])
        self.assertEqual(normalize_tree([]), [])
        self.assertEqual(normalize_tree(""), [])
        self.assertEqual(tree_keys(normalize_tree([None, 5.5])), ["5.5"])


class TestLoad(unittest.TestCase):
    def test_json_string(self) -> None:
        self.assertEqual(
            tree_keys(normalize_tree('[{"label": "Eviction", "key": "HO"}]')), ["HO"]
        )

    def test_python_literal_string(self) -> None:
        # This is the shape a data attribute arrives in, since docassemble
        # renders custom parameters with str().
        self.assertEqual(
            tree_keys(normalize_tree("[{'label': 'Eviction', 'key': 'HO'}]")), ["HO"]
        )

    def test_bad_string_is_ignored_rather_than_raising(self) -> None:
        self.assertIsNone(_load("this is not a literal"))
        self.assertEqual(normalize_tree("this is not a literal"), [])


class TestSelectedFrom(unittest.TestCase):
    def test_json_array(self) -> None:
        self.assertEqual(_selected_from('["a", "b"]'), ["a", "b"])

    def test_empty(self) -> None:
        self.assertEqual(_selected_from(""), [])
        self.assertEqual(_selected_from(None), [])
        self.assertEqual(_selected_from([]), [])

    def test_dict_keeps_only_true_values(self) -> None:
        self.assertEqual(_selected_from({"a": True, "b": False, "c": True}), ["a", "c"])

    def test_list(self) -> None:
        self.assertEqual(_selected_from(["a", "b"]), ["a", "b"])

    def test_comma_separated_fallback(self) -> None:
        self.assertEqual(_selected_from("a, b"), ["a", "b"])


CHOICES = [
    {
        "label": "Housing",
        "children": [
            {"label": "Eviction", "key": "HO-01"},
            {"label": "Repairs", "key": "HO-02"},
        ],
    },
    {"label": "Something else", "key": "OTHER"},
]


class TestValidate(unittest.TestCase):
    def test_known_keys_pass(self) -> None:
        self.assertTrue(
            ALTreeSelect.validate('["HO-01"]', "issues", {"choices": CHOICES})
        )

    def test_empty_passes(self) -> None:
        self.assertTrue(ALTreeSelect.validate("", "issues", {"choices": CHOICES}))

    def test_unknown_key_raises(self) -> None:
        with self.assertRaises(Exception):
            ALTreeSelect.validate('["NOPE"]', "issues", {"choices": CHOICES})

    def test_max_is_enforced(self) -> None:
        with self.assertRaises(Exception):
            ALTreeSelect.validate(
                '["HO-01", "HO-02"]', "issues", {"choices": CHOICES, "max": 1}
            )

    def test_min_is_enforced_only_once_something_is_chosen(self) -> None:
        self.assertTrue(
            ALTreeSelect.validate("", "issues", {"choices": CHOICES, "min": 2})
        )
        with self.assertRaises(Exception):
            ALTreeSelect.validate('["HO-01"]', "issues", {"choices": CHOICES, "min": 2})

    def test_validate_without_choices_does_not_raise(self) -> None:
        self.assertTrue(ALTreeSelect.validate('["anything"]', "issues", {}))


class TestTransform(unittest.TestCase):
    def test_every_key_is_present(self) -> None:
        result = ALTreeSelect.transform('["HO-01"]', "issues", {"choices": CHOICES})
        self.assertEqual(sorted(result.keys()), ["HO-01", "HO-02", "OTHER"])
        self.assertTrue(result["HO-01"])
        self.assertFalse(result["HO-02"])
        self.assertEqual(result.true_values(), ["HO-01"])
        self.assertTrue(result.any_true())

    def test_empty_answer_is_all_false(self) -> None:
        result = ALTreeSelect.transform("", "issues", {"choices": CHOICES})
        self.assertEqual(sorted(result.keys()), ["HO-01", "HO-02", "OTHER"])
        self.assertFalse(result.any_true())

    def test_instance_name_is_the_variable(self) -> None:
        result = ALTreeSelect.transform("", "my_var", {"choices": CHOICES})
        self.assertEqual(result.instanceName, "my_var")
        self.assertTrue(result.gathered)

    def test_choices_from_code_parameter(self) -> None:
        result = ALTreeSelect.transform('["OTHER"]', "issues", {"code": CHOICES})
        self.assertEqual(sorted(result.keys()), ["HO-01", "HO-02", "OTHER"])
        self.assertTrue(result["OTHER"])

    def test_without_choices_keeps_what_was_chosen(self) -> None:
        result = ALTreeSelect.transform('["HO-01"]', "issues", {})
        self.assertEqual(list(result.keys()), ["HO-01"])
        self.assertTrue(result["HO-01"])


class TestDefaultFor(unittest.TestCase):
    def test_round_trip_through_a_dadict(self) -> None:
        stored = ALTreeSelect.transform('["HO-01"]', "issues", {"choices": CHOICES})
        self.assertEqual(
            ALTreeSelect.default_for(stored, "issues", {"choices": CHOICES}),
            '["HO-01"]',
        )

    def test_nothing_selected_gives_an_empty_string(self) -> None:
        stored = ALTreeSelect.transform("", "issues", {"choices": CHOICES})
        self.assertEqual(
            ALTreeSelect.default_for(stored, "issues", {"choices": CHOICES}), ""
        )

    def test_a_plain_list_default_works(self) -> None:
        self.assertEqual(
            ALTreeSelect.default_for(["HO-01", "HO-02"], "issues", {}),
            '["HO-01", "HO-02"]',
        )


class TestJavaScriptAsset(unittest.TestCase):
    def test_css_is_inlined_into_the_script(self) -> None:
        self.assertIn("al-tree-select", ALTreeSelect.javascript)
        # The placeholder must have been replaced with the real stylesheet.
        self.assertNotIn("__AL_TREE_SELECT_CSS__", ALTreeSelect.javascript)
        self.assertIn(".al-tree-children", ALTreeSelect.javascript)

    def test_registered_under_the_expected_name(self) -> None:
        from docassemble.base.functions import custom_types

        self.assertIn("al_tree_select", custom_types)
        self.assertTrue(custom_types["al_tree_select"]["is_object"])


if __name__ == "__main__":
    unittest.main()
