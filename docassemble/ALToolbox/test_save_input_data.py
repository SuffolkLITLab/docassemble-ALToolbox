# do not pre-load
"""Exercise survey serialization at the JSON storage boundary without a server."""

import importlib.util
import json
import sys
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from docassemble.base.functions import safe_json
from docassemble.base.util import DADict, DAFile, DAList, DAObject, Individual


@pytest.fixture
def save_record(monkeypatch):
    # Import the actual source with only the webapp/database boundary replaced.
    # Loading an isolated module avoids leaking the fake database into other tests
    # and avoids webapp's server configuration requirements during collection.
    storage = Mock(side_effect=lambda **kwargs: SimpleNamespace(**kwargs))
    session = Mock()
    helpers = ModuleType("docassemble.webapp.jsonstorage.helpers")
    helpers.JsonStorage = storage
    extensions = ModuleType("docassemble.webapp.extensions")
    extensions.db = SimpleNamespace(session=session)
    monkeypatch.setitem(sys.modules, helpers.__name__, helpers)
    monkeypatch.setitem(sys.modules, extensions.__name__, extensions)

    spec = importlib.util.spec_from_file_location(
        "save_input_data_under_test", Path(__file__).with_name("save_input_data.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module, "get_current_info", lambda: {"yaml_filename": "survey.yml"}
    )
    monkeypatch.setattr(module, "random_alphanumeric", lambda length: "a" * length)

    # Simulate the json.dumps call made when SQLAlchemy commits a JSON column.
    # This catches the original failure even for deeply nested values.
    session.commit.side_effect = lambda: json.dumps(session.add.call_args.args[0].data)

    def save(**kwargs):
        assert module.save_input_data(**kwargs) is None
        session.add.assert_called_once()
        session.commit.assert_called_once_with()
        return session.add.call_args.args[0]

    return save


@pytest.mark.parametrize(
    "value, expected, field_type",
    [
        (None, None, "text"),
        (True, True, "bool"),
        (False, False, "bool"),
        (42, 42, "int"),
        (1.25, 1.25, "float"),
        ("Feedback", "Feedback", "text"),
        (Decimal("12.50"), 12.5, "float"),
        (date(2026, 1, 2), "2026-01-02", "date"),
        (
            datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            "2026-01-02T03:04:05+00:00",
            "date",
        ),
        (time(3, 4, 5), "03:04:05", "text"),
    ],
)
def test_primitives_dates_and_decimals(save_record, value, expected, field_type):
    entry = save_record(input_dict={"answer": value})
    assert entry.data["answer"] == expected
    assert type(entry.data["answer"]) is type(expected)
    assert entry.data["field_type_list"] == {"answer": field_type}


def test_people_and_gathered_lists_save_display_text(save_record):
    john = Individual("users[0]")
    john.name.first = "John"
    john.name.last = "Smith"
    jane = Individual("users[1]")
    jane.name.first = "Jane"
    jane.name.last = "Smith"
    people = DAList("users", elements=[john, jane], gathered=True)

    entry = save_record(input_dict={"person": john, "people": people})
    assert entry.data["person"] == "John Smith"
    assert entry.data["people"] == "John Smith and Jane Smith"


def test_inherited_custom_string_method(save_record):
    class Label:
        def __str__(self):
            return "A useful label"

    class InheritedLabel(Label):
        pass

    entry = save_record(input_dict={"answer": InheritedLabel()})
    assert entry.data["answer"] == "A useful label"


def test_default_object_strings_fall_back_to_safe_json(save_record):
    details = DAObject("details", amount=Decimal("2.50"))
    details.self_reference = details
    opaque = object()
    entry = save_record(input_dict={"details": details, "opaque": opaque})
    assert entry.data["details"] == safe_json(details)
    assert entry.data["details"]["amount"] == 2.5
    assert entry.data["opaque"] is None


def test_named_daobject_uses_its_name(save_record):
    entry = save_record(input_dict={"answer": DAObject("answer", name="Display name")})
    assert entry.data["answer"] == "Display name"


@pytest.mark.parametrize("error", [NameError, TypeError, ValueError])
def test_failed_string_method_falls_back_to_safe_json(save_record, error):
    class BrokenDisplay(DAObject):
        def __str__(self):
            raise error("Cannot display this object")

    answer = BrokenDisplay("answer", value=Decimal("3.50"))
    entry = save_record(input_dict={"answer": answer})
    assert entry.data["answer"] == safe_json(answer)
    assert entry.data["answer"]["value"] == 3.5


def test_native_containers_remain_structured(save_record):
    nested = {"amounts": [Decimal("2.50")], "date": date(2026, 1, 2)}
    entry = save_record(
        input_dict={
            "nested": nested,
            "tuple": (date(2026, 1, 2), Decimal("2.50")),
            "set": {Decimal("2.50")},
        }
    )
    assert entry.data["nested"] == {"amounts": [2.5], "date": "2026-01-02"}
    assert entry.data["tuple"] == ["2026-01-02", 2.5]
    assert entry.data["set"] == [2.5]
    assert nested["amounts"] == [Decimal("2.50")]
    assert isinstance(nested["date"], date)


def test_checkbox_values_are_flattened_and_serialized(save_record):
    choices = DADict(
        "choices",
        elements={
            "selected": True,
            "unselected": False,
            42: Decimal("2.50"),
            "date": date(2026, 1, 2),
        },
    )
    entry = save_record(input_dict={"choices": choices})
    assert entry.data == {
        "title": "",
        "field_type_list": {"choices": "checkboxes"},
        "choices_selected": True,
        "choices_unselected": False,
        "choices_42": 2.5,
        "choices_date": "2026-01-02",
    }
    assert isinstance(choices.elements[42], Decimal)


def test_files_use_their_display_text(save_record):
    attachment = DAFile(
        "attachment", number=42, filename="report.pdf", mimetype="application/pdf"
    )
    entry = save_record(input_dict={"attachment": attachment})
    assert entry.data["attachment"] == str(attachment)


def test_incomplete_files_can_be_serialized(save_record):
    attachment = DAFile("attachment", number=42, filename="report.pdf")
    entry = save_record(input_dict={"attachment": attachment})
    assert entry.data["attachment"] == safe_json(attachment)


@pytest.mark.parametrize("input_dict", [None, {}])
def test_empty_input_preserves_record_metadata(save_record, input_dict):
    entry = save_record(title="Survey", input_dict=input_dict, tags=["feedback"])
    assert entry.data == {"title": "Survey", "field_type_list": {}}
    assert entry.filename == "survey.yml"
    assert entry.key == "a" * 32
    assert entry.tags == ["feedback"]
    assert entry.persistent is False
